import sqlite3
import json
import os

DB_PATH = "aethersense.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS login_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT,
                user TEXT,
                timestamp TEXT,
                success INTEGER,
                attempt_rate_30s REAL,
                unique_users_targeted REAL,
                failure_rate REAL,
                inter_arrival_variance REAL,
                threshold_proximity REAL,
                session_duration_delta REAL,
                endpoint_entropy REAL,
                user_agent_consistency REAL,
                geo_velocity REAL,
                keystroke_entropy REAL,
                baseline_deviation_7d REAL,
                request_regularity REAL,
                suspicion_composite REAL,
                session_entropy REAL,
                device_change_score REAL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT,
                risk_score REAL,
                iso_score REAL,
                lstm_score REAL,
                probe_score REAL,
                confidence REAL,
                attack_type TEXT,
                status TEXT,
                llm_narration TEXT,
                timestamp TEXT
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS blocked_ips (
                ip TEXT PRIMARY KEY,
                block_reason TEXT,
                evidence_json TEXT,
                blocked_at TEXT,
                blocked_by TEXT,
                expires_at TEXT
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS honeypot_triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT,
                endpoint_hit TEXT,
                trigger_type TEXT,
                timestamp TEXT,
                fake_response_sent TEXT
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS probing_sessions (
                ip TEXT PRIMARY KEY,
                threshold_proximity_history TEXT,
                session_count INTEGER,
                escalated INTEGER,
                first_seen TEXT,
                last_seen TEXT
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ip_baselines (
                ip TEXT PRIMARY KEY,
                feature_vector_json TEXT,
                last_updated TEXT,
                event_count INTEGER,
                persona_type TEXT
            )
            """
        )

        conn.commit()
    finally:
        conn.close()


def clear_all():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM login_events")
        cur.execute("DELETE FROM alerts")
        cur.execute("DELETE FROM blocked_ips")
        cur.execute("DELETE FROM honeypot_triggers")
        cur.execute("DELETE FROM probing_sessions")
        cur.execute("DELETE FROM ip_baselines")
        conn.commit()
    finally:
        conn.close()


def get_connection():
    return sqlite3.connect(DB_PATH, row_factory=sqlite3.Row)


init_db()
