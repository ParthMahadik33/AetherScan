import datetime
import json
import threading
import time
import warnings

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

try:
    from . import attack_launcher
    from . import database
    from . import honeypot
    from . import llm_narrator
    from . import probing_detector
    from . import scoring
    from . import aml_scorer
    from . import transaction_db
    from . import identity_scorer
    from . import identity_db
except ImportError:
    import attack_launcher
    import database
    import honeypot
    import llm_narrator
    import probing_detector
    import scoring
    import aml_scorer
    import transaction_db
    import identity_scorer
    import identity_db


load_dotenv()

app = Flask(__name__)
import logging
logging.getLogger("werkzeug").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*Eventlet is deprecated.*")

CORS(app, resources={r"*": {"origins": "*"}})
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")


@app.route("/api/test", methods=["GET", "POST"])
def test_route():
    return jsonify({"status": "ok"})


database.init_db()
transaction_db.init_db()
identity_db.init_db()
attack_launcher.ATTACK_MAP["smurfing"] = "simulation.attack_smurfing"
attack_launcher.ATTACK_MAP["synthetic_identity"] = "simulation.attack_synthetic_identity"


blocked_ips = set()
captcha_ips = set()
rate_limited_ips = {}
active_attacks = {}
ip_session_store = {}
attack_lock = threading.Lock()


def now_iso():
    return datetime.datetime.utcnow().isoformat()

KNOWN_VPN_ASNS = {"AS9009", "AS20473", "AS62888", "AS209854", "AS132203"}

def is_vpn_ip(ip):
    # Simulate ASN lookup — in production use ip-api.com or ipinfo.io
    # For simulation: if IP starts with 103.21 treat as potential VPN
    return ip.startswith("103.21")


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


    if attack_type == "Credential_Stuffing" and status in ("ALERT", "BLOCKED"):
        # Invalidate any sessions that were created from this IP
        ip_session_store[ip] = {
            "invalidated": True,
            "reason": "Spray attack detected — all sessions from this IP invalidated",
            "force_reauth": True
        }
        socketio.emit("action_taken", {
            "ip": ip,
            "action": "ALL_SESSIONS_INVALIDATED",
            "reason": "Password spray detected — forcing re-authentication on all accounts accessed from this IP",
        })

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

    # ATO step-up auth — suspicious travel speed but not physically impossible
    # Instead of hard blocking, challenge with MFA like industry standard
    # This handles the "2000-5000 km/h" range from scoring.py Override 2
    if attack_type == "ATO_Impossible_Travel" and status == "ALERT":
        captcha_ips.add(ip)
        rate_limited_ips[ip] = current_time + 120  # 2 min window to complete MFA
        socketio.emit("action_taken", {
            "ip": ip,
            "action": "MFA_REQUIRED",
            "reason": "Suspicious travel speed detected — step-up authentication required. If this is you, please verify via MFA.",
            "geo_context": "Login detected from unexpected location. Possible causes: VPN, travel, or account compromise.",
        })
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

    probe_result = probing_detector.check_probing(ip, features)
    probe_score = float(probe_result.get("probe_score", 0.0))

    expire_ts = rate_limited_ips.get(ip)
    if expire_ts:
        remaining = int(max(0, expire_ts - time.time()))
        if remaining > 0:
            probe_score = min(100.0, probe_score + 40.0)
        else:
            rate_limited_ips.pop(ip, None)

    score_result = scoring.compute_risk_score(ip, features, probe_score=probe_score)
    attack_type = derive_attack_type(features)
    status = score_result["status"]

    if ip in blocked_ips:
        socketio.emit("threat_update", {
            "ip": ip, "status": "BLOCKED", "risk_score": 100,
            "iso_score": 0, "lstm_score": 0, "probe_score": 0,
            "confidence": 100, "attack_type": "Known_Blocked_IP",
            "timestamp": now_iso()
        })
        return jsonify({"status": "BLOCKED", "action": "REQUEST_REJECTED", "risk_score": 100}), 403

    risk_score = float(score_result["risk_score"])

    if probe_result.get("is_probing") and status in {"NORMAL", "MONITORING"}:
        status = "BLOCKED"  # was "PROBING" — probing = instant block, no escalation needed
        risk_score = max(risk_score, 85.0)

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


@app.route("/api/attack/start", methods=["POST", "OPTIONS"])
@app.route("/api/attack/start/", methods=["POST", "OPTIONS"])
def api_attack_start():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.get_json(silent=True) or {}
    attack_type = data.get("attack_type")
    print(f"[api_attack_start] attack_type={attack_type}")
    result = attack_launcher.start_attack(attack_type, active_attacks)
    return jsonify(result)


@app.route("/api/attack/stop", methods=["POST", "OPTIONS"])
@app.route("/api/attack/stop/", methods=["POST", "OPTIONS"])
def api_attack_stop():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.get_json(silent=True) or {}
    attack_type = data.get("attack_type")
    result = attack_launcher.stop_attack(attack_type, active_attacks)
    return jsonify(result)


@app.route("/api/attack/status", methods=["GET"])
def api_attack_status():
    return jsonify(attack_launcher.get_status(active_attacks))


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


@app.route("/api/transaction", methods=["POST"])
def api_transaction():
    data = request.get_json(silent=True) or {}
    account_id = data.get("account_id")
    amount = data.get("amount")
    recipient_id = data.get("recipient_id")
    recipient_name = data.get("recipient_name")
    timestamp = data.get("timestamp", now_iso())

    score_result = aml_scorer.score_transaction(account_id, amount, recipient_id, timestamp)
    
    status = score_result["status"]
    action = score_result["action"]
    
    # Save to DB
    txn_data = {
        "account_id": account_id,
        "recipient_id": recipient_id,
        "recipient_name": recipient_name,
        "amount": amount,
        "timestamp": timestamp,
        "status": status if action != "hold" else "HELD",
        "risk_score": score_result["risk_score"],
        "velocity_score": score_result["velocity_score"],
        "proximity_score": score_result["proximity_score"],
        "fanout_score": score_result["fanout_score"],
        "cumulative_score": score_result["cumulative_score"]
    }
    
    if action == "reverse_all":
        txn_data["status"] = "REVERSED"
        
    txn_id = transaction_db.insert_transaction(txn_data)
    
    if action == "hold":
        transaction_db.add_to_escrow(txn_id, account_id, amount)
    elif action == "reverse_all":
        transaction_db.resolve_escrow(account_id, "REVERSED")
        # Update current also if it was previously set. 
        socketio.emit("aml_threat_update", {
            "account_id": account_id,
            "action": "reverse_all",
            "message": f"Account {account_id} blocked. All holdings reversed."
        })
        # Record AML Alert
        transaction_db.insert_aml_alert({
            "account_id": account_id,
            "risk_score": score_result["risk_score"],
            "status": "BLOCKED",
            "action_taken": "reverse_all",
            "signal_breakdown": score_result,
            "narrative": f"Structuring confirmed. Account frozen."
        })
    elif status == "ALERT" and action == "hold":
        transaction_db.insert_aml_alert({
            "account_id": account_id,
            "risk_score": score_result["risk_score"],
            "status": "ALERT",
            "action_taken": "hold",
            "signal_breakdown": score_result,
            "narrative": f"Suspicious transaction held in escrow."
        })

    # Prepare return and emit
    res = {
        "transaction_id": txn_id,
        "account_id": account_id,
        "amount": amount,
        "recipient_name": recipient_name,
        "status": "HELD" if action == "hold" else ("REVERSED" if action == "reverse_all" else "COMPLETED"),
        "action": action,
        "risk_score": score_result["risk_score"],
        "velocity_score": score_result["velocity_score"],
        "proximity_score": score_result["proximity_score"],
        "fanout_score": score_result["fanout_score"],
        "cumulative_score": score_result["cumulative_score"],
        "narrative": "Pattern anomalous." if score_result["risk_score"] > 55 else "",
        "timestamp": timestamp
    }
    
    socketio.emit("aml_update", res)
    return jsonify(res), 200

@app.route("/api/transactions/<account_id>", methods=["GET"])
def api_transactions(account_id):
    txns = transaction_db.get_transactions(account_id, limit=20)
    return jsonify(txns), 200

@app.route("/api/aml/alerts", methods=["GET"])
def api_aml_alerts():
    alerts = transaction_db.get_aml_alerts(limit=50)
    return jsonify(alerts), 200

@app.route("/api/aml/account/<account_id>", methods=["GET"])
def api_aml_account(account_id):
    txns = transaction_db.get_transactions(account_id, limit=1000)
    total_attempted = sum(t["amount"] for t in txns)
    held_txns = [t for t in txns if t["status"] == "HELD"]
    reversed_txns = [t for t in txns if t["status"] == "REVERSED"]
    total_protected = sum(t["amount"] for t in reversed_txns) + sum(t["amount"] for t in held_txns)
    balance = 500000 - total_attempted + total_protected
    is_blocked = account_id in aml_scorer.blocked_accounts
    return jsonify({
        "balance": balance,
        "blocked": is_blocked,
        "total_attempted": total_attempted,
        "total_protected": total_protected
    }), 200

@app.route("/api/aml/reset", methods=["POST"])
def api_aml_reset():
    aml_scorer.reset_state()
    transaction_db.clear_db()
    return jsonify({"status": "cleared"}), 200

# ----------------- IDENTITY ATTACK ENDPOINTS -----------------

@app.route("/api/identity/create-account", methods=["POST"])
def api_identity_create_account():
    data = request.get_json(silent=True) or {}
    account_id = data.get("account_id")
    device_fingerprint = data.get("device_fingerprint")
    
    score_result = identity_scorer.score_account_creation(
        account_id=account_id,
        name=data.get("name"),
        pan_number=data.get("pan_number"),
        aadhaar_last4=data.get("aadhaar_last4"),
        device_fingerprint=device_fingerprint,
        form_fill_duration_ms=data.get("form_fill_duration_ms"),
        screen_resolution=data.get("screen_resolution"),
        timezone=data.get("timezone"),
        browser_ua=data.get("browser_ua"),
        timestamp=data.get("timestamp", now_iso())
    )
    
    status = score_result["status"]
    action = score_result["action"]
    
    # Enrich data for DB
    data.update({
        "status": status,
        "risk_score": score_result["risk_score"],
        "device_score": score_result["device_score"],
        "entropy_score": score_result["entropy_score"],
        "velocity_score": score_result["velocity_score"]
    })
    
    identity_db.insert_account(data)
    
    if action == "suspend_all":
        # Retroactive suspensension for previously created accounts on device
        accounts = identity_db.get_accounts_by_device(device_fingerprint)
        for acc in accounts:
            if acc["status"] != "BLOCKED":
                identity_db.update_account_status(acc["account_id"], "BLOCKED")
        
        # Identity Alert
        identity_db.insert_identity_alert({
            "device_fingerprint": device_fingerprint,
            "account_ids": [a["account_id"] for a in accounts],
            "total_accounts": len(accounts),
            "risk_score": score_result["risk_score"],
            "action": "suspend_all",
            "narrative": score_result["narrative"]
        })
        
    res = {
        "event_type": "account_created",
        "account_id": account_id,
        "name": data.get("name"),
        "device_fingerprint": device_fingerprint,
        "device_collision_count": score_result["device_collision_count"],
        "status": status,
        "action": action,
        "risk_score": score_result["risk_score"],
        "device_score": score_result["device_score"],
        "entropy_score": score_result["entropy_score"],
        "velocity_score": score_result["velocity_score"],
        "narrative": score_result["narrative"],
        "timestamp": now_iso()
    }
    
    socketio.emit("identity_update", res)
    return jsonify(res), 200

@app.route("/api/identity/apply-credit", methods=["POST"])
def api_identity_apply_credit():
    data = request.get_json(silent=True) or {}
    account_id = data.get("account_id")
    requested_amount = data.get("requested_amount", 50000)
    timestamp = now_iso()
    
    # calculate age and TXN counts
    account_age_seconds = 0
    transaction_count = 0
    
    accounts = identity_db.get_all_accounts(limit=100)
    for acc in accounts:
        if acc["account_id"] == account_id:
            try:
                created = datetime.datetime.fromisoformat(acc["created_at"])
                account_age_seconds = (datetime.datetime.utcnow() - created).total_seconds()
            except:
                pass
            break
            
    # Lookup transactions
    txns = transaction_db.get_transactions(account_id, limit=100)
    transaction_count = len(txns)
    
    score_result = identity_scorer.score_credit_application(
        account_id, requested_amount, account_age_seconds, transaction_count, timestamp
    )
    
    data.update({
        "account_age_seconds": account_age_seconds,
        "transaction_count": transaction_count,
        "status": score_result["status"],
        "risk_score": score_result["risk_score"],
        "hunger_score": score_result["hunger_score"],
        "maturity_score": score_result["maturity_score"],
        "narrative": score_result["narrative"]
    })
    
    app_id = identity_db.insert_credit_application(data)
    
    if score_result["action"] == "reject_credit":
        identity_db.update_account_status(account_id, "BLOCKED")
        
    res = {
        "event_type": "credit_applied",
        "application_id": app_id,
        "account_id": account_id,
        "status": score_result["status"],
        "action": score_result["action"],
        "risk_score": score_result["risk_score"],
        "hunger_score": score_result["hunger_score"],
        "maturity_score": score_result["maturity_score"],
        "narrative": score_result["narrative"],
        "timestamp": timestamp
    }
    
    socketio.emit("identity_update", res)
    return jsonify(res), 200

@app.route("/api/identity/accounts", methods=["GET"])
def api_identity_accounts():
    return jsonify(identity_db.get_all_accounts(limit=20)), 200

@app.route("/api/identity/alerts", methods=["GET"])
def api_identity_alerts():
    return jsonify(identity_db.get_identity_alerts(limit=50)), 200

@app.route("/api/identity/stats", methods=["GET"])
def api_identity_stats():
    return jsonify(identity_db.get_device_stats()), 200

@app.route("/api/identity/reset", methods=["POST"])
def api_identity_reset():
    identity_scorer.reset_state()
    identity_db.reset_database()
    return jsonify({"status": "cleared"}), 200


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, log_output=False)
