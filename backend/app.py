import datetime
import json
import threading
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO

import attack_launcher
import database
import honeypot
import llm_narrator
import probing_detector
import scoring


load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"*": {"origins": "*"}})
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

database.init_db()


blocked_ips = set()
captcha_ips = set()
rate_limited_ips = {}
active_attacks = {}
ip_session_store = {}
attack_lock = threading.Lock()


def now_iso():
    return datetime.datetime.utcnow().isoformat()


def get_db_conn():
    return database.get_connection()


def derive_attack_type(features):
    if features.get("geo_velocity", 0) > 500:
        return "ATO_Impossible_Travel"
    if features.get("keystroke_entropy", 1) < 0.05:
        return "Bot_Automation"
    if features.get("unique_users_targeted", 0) > 10:
        return "Credential_Stuffing"
    if features.get("endpoint_entropy", 0) > 0.9:
        return "API_Scraping"
    return "Behavioral_Anomaly"


def execute_actions(ip, status, risk_score, attack_type):
    current_time = time.time()

    if status == "BLOCKED" or risk_score >= 85:
        blocked_ips.add(ip)
        ip_session_store[ip] = {"invalidated": True, "reason": attack_type}

        blocked_at = now_iso()
        expires_at = (
            datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        ).isoformat()
        evidence_json = json.dumps(
            {"status": status, "risk_score": risk_score, "attack_type": attack_type}
        )

        conn = get_db_conn()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO blocked_ips
                (ip, block_reason, evidence_json, blocked_at, blocked_by, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    ip,
                    attack_type,
                    evidence_json,
                    blocked_at,
                    "AetherSense-AutoResponse",
                    expires_at,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        socketio.emit(
            "action_taken",
            {
                "ip": ip,
                "action": "IP_BLOCKED",
                "reason": attack_type,
                "session_invalidated": True,
            },
        )
        return

    if status == "ALERT" or risk_score >= 70:
        captcha_ips.add(ip)
        rate_limited_ips[ip] = current_time + 60
        socketio.emit(
            "action_taken",
            {
                "ip": ip,
                "action": "CAPTCHA_REQUIRED + RATE_LIMITED_60s",
                "reason": attack_type,
            },
        )
        return

    if status == "HONEYPOT":
        blocked_ips.add(ip)
        blocked_at = now_iso()
        evidence_json = json.dumps(
            {"status": status, "risk_score": risk_score, "attack_type": "honeypot_triggered"}
        )

        conn = get_db_conn()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO blocked_ips
                (ip, block_reason, evidence_json, blocked_at, blocked_by, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    ip,
                    "honeypot_triggered",
                    evidence_json,
                    blocked_at,
                    "Honeypot-Engine",
                    None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        socketio.emit(
            "action_taken",
            {
                "ip": ip,
                "action": "HONEYPOT_BLOCK",
                "reason": "Trap triggered — instant block, no ML needed",
            },
        )
        return

    if status == "MONITORING":
        rate_limited_ips[ip] = current_time + 30
        socketio.emit(
            "action_taken",
            {
                "ip": ip,
                "action": "INCREASED_LOGGING + SOFT_RATE_LIMIT_30s",
                "reason": attack_type,
            },
        )


def parse_features(payload):
    return {name: float(payload.get(name, 0.0)) for name in scoring.FEATURES}


def maybe_emit_llm(alert_payload):
    status = alert_payload.get("status")
    if status not in {"ALERT", "BLOCKED", "HONEYPOT"}:
        return

    def _worker():
        narration = llm_narrator.generate_threat_narrative(alert_payload)
        socketio.emit(
            "llm_ready",
            {
                "ip": alert_payload.get("ip"),
                "status": status,
                "attack_type": alert_payload.get("attack_type"),
                "narration": narration,
                "timestamp": now_iso(),
            },
        )

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


@app.post("/api/event")
def api_event():
    payload = request.get_json(silent=True) or {}
    ip = str(payload.get("ip") or request.remote_addr or "0.0.0.0")
    user = str(payload.get("user", "unknown"))
    success = int(bool(payload.get("success", 0)))
    features = parse_features(payload)

    if ip in blocked_ips:
        return (
            jsonify(
                {
                    "status": "BLOCKED",
                    "action": "REQUEST_REJECTED",
                    "risk_score": 100,
                }
            ),
            403,
        )

    expire_ts = rate_limited_ips.get(ip)
    if expire_ts:
        remaining = int(max(0, expire_ts - time.time()))
        if remaining > 0:
            return (
                jsonify(
                    {
                        "status": "RATE_LIMITED",
                        "action": "SLOW_DOWN",
                        "retry_after": remaining,
                    }
                ),
                429,
            )
        rate_limited_ips.pop(ip, None)

    probe_result = probing_detector.check_probing(ip, features)
    probe_score = float(probe_result.get("probe_score", 0.0))

    score_result = scoring.compute_risk_score(ip, features, probe_score=probe_score)
    attack_type = derive_attack_type(features)
    status = score_result["status"]

    if probe_result.get("is_probing") and status in {"NORMAL", "MONITORING"}:
        status = "PROBING"

    risk_score = float(score_result["risk_score"])
    execute_actions(ip, status, risk_score, attack_type)

    timestamp = now_iso()
    conn = get_db_conn()
    try:
        conn.execute(
            """
            INSERT INTO login_events (
                ip, user, timestamp, success,
                attempt_rate_30s, unique_users_targeted, failure_rate, inter_arrival_variance,
                threshold_proximity, session_duration_delta, endpoint_entropy, user_agent_consistency,
                geo_velocity, keystroke_entropy, baseline_deviation_7d, request_regularity,
                suspicion_composite, session_entropy, device_change_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ip,
                user,
                timestamp,
                success,
                features["attempt_rate_30s"],
                features["unique_users_targeted"],
                features["failure_rate"],
                features["inter_arrival_variance"],
                features["threshold_proximity"],
                features["session_duration_delta"],
                features["endpoint_entropy"],
                features["user_agent_consistency"],
                features["geo_velocity"],
                features["keystroke_entropy"],
                features["baseline_deviation_7d"],
                features["request_regularity"],
                features["suspicion_composite"],
                features["session_entropy"],
                features["device_change_score"],
            ),
        )

        if risk_score >= 50:
            conn.execute(
                """
                INSERT INTO alerts (
                    ip, risk_score, iso_score, lstm_score, probe_score, confidence,
                    attack_type, status, llm_narration, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ip,
                    risk_score,
                    float(score_result["iso_score"]),
                    float(score_result["lstm_score"]),
                    probe_score,
                    float(score_result["confidence"]),
                    attack_type,
                    status,
                    None,
                    timestamp,
                ),
            )
        conn.commit()
    finally:
        conn.close()

    result = {
        "ip": ip,
        "user": user,
        "success": success,
        "risk_score": risk_score,
        "iso_score": float(score_result["iso_score"]),
        "lstm_score": float(score_result["lstm_score"]),
        "probe_score": probe_score,
        "confidence": float(score_result["confidence"]),
        "status": status,
        "attack_type": attack_type,
        "features": features,
        "timestamp": timestamp,
    }

    maybe_emit_llm(result)
    socketio.emit("threat_update", result)

    if status == "BLOCKED":
        return jsonify(result), 403
    if status == "RATE_LIMITED":
        return jsonify(result), 429
    return jsonify(result), 200


@app.get("/api/alerts")
def api_alerts():
    conn = get_db_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 50"
        ).fetchall()
        return jsonify([dict(row) for row in rows]), 200
    finally:
        conn.close()


@app.get("/api/health")
def api_health():
    return (
        jsonify(
            {
                "isolation_forest": "active",
                "lstm_autoencoder": "active",
                "probing_detector": "active",
                "honeypot_engine": "active",
                "blocked_ips_count": len(blocked_ips),
                "captcha_ips_count": len(captcha_ips),
                "rate_limited_count": len(rate_limited_ips),
            }
        ),
        200,
    )


@app.get("/api/clear")
def api_clear():
    database.clear_all()
    blocked_ips.clear()
    captcha_ips.clear()
    rate_limited_ips.clear()
    ip_session_store.clear()
    return jsonify({"status": "cleared"}), 200


@app.post("/api/attack/start")
def api_attack_start():
    payload = request.get_json(silent=True) or {}
    attack_type = str(payload.get("attack_type", "")).strip()
    if not attack_type:
        return jsonify({"status": "error", "message": "attack_type is required"}), 400

    with attack_lock:
        result = attack_launcher.start_attack(attack_type, active_attacks)
    status_code = 200 if result.get("status") in {"started", "already_running"} else 404
    return jsonify(result), status_code


@app.post("/api/attack/stop")
def api_attack_stop():
    payload = request.get_json(silent=True) or {}
    attack_type = str(payload.get("attack_type", "")).strip()
    if not attack_type:
        return jsonify({"status": "error", "message": "attack_type is required"}), 400

    with attack_lock:
        result = attack_launcher.stop_attack(attack_type, active_attacks)
    return jsonify(result), 200


@app.get("/api/attack/status")
def api_attack_status():
    with attack_lock:
        data = attack_launcher.get_status(active_attacks)
    return jsonify(data), 200


@app.get("/api/actions/log")
def api_actions_log():
    conn = get_db_conn()
    try:
        rows = conn.execute(
            "SELECT ip, block_reason, blocked_at, blocked_by, expires_at FROM blocked_ips ORDER BY blocked_at DESC"
        ).fetchall()
        return jsonify([dict(row) for row in rows]), 200
    finally:
        conn.close()


def _handle_honeypot(endpoint):
    ip = str(request.remote_addr or "0.0.0.0")
    timestamp = now_iso()
    fake_response = honeypot.get_fake_response(endpoint)

    conn = get_db_conn()
    try:
        conn.execute(
            """
            INSERT INTO honeypot_triggers (
                ip, endpoint_hit, trigger_type, timestamp, fake_response_sent
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (ip, endpoint, "endpoint", timestamp, json.dumps(fake_response)),
        )
        conn.commit()
    finally:
        conn.close()

    execute_actions(ip, "HONEYPOT", 100, "honeypot_endpoint")
    return jsonify(fake_response), 200


@app.route("/api/v1/internal/users", methods=["GET", "POST"])
def hp_internal_users():
    return _handle_honeypot("/api/v1/internal/users")


@app.route("/api/v1/admin/dump", methods=["GET"])
def hp_admin_dump():
    return _handle_honeypot("/api/v1/admin/dump")


@app.route("/api/v1/system/config", methods=["GET"])
def hp_system_config():
    return _handle_honeypot("/api/v1/system/config")


@app.route("/api/v1/debug/login", methods=["POST"])
def hp_debug_login():
    return _handle_honeypot("/api/v1/debug/login")


@app.route("/api/v1/hidden/export", methods=["GET"])
def hp_hidden_export():
    return _handle_honeypot("/api/v1/hidden/export")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
