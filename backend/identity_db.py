import sqlite3
import json
import uuid
import datetime

DB_FILE = 'identity_fraud.db'

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS synthetic_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT UNIQUE,
                name TEXT,
                pan_number TEXT,
                aadhaar_last4 TEXT,
                device_fingerprint TEXT,
                screen_resolution TEXT,
                timezone TEXT,
                browser_ua TEXT,
                form_fill_duration_ms INTEGER,
                created_at TEXT,
                status TEXT,
                risk_score REAL,
                device_score REAL,
                entropy_score REAL,
                velocity_score REAL
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS credit_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT,
                requested_amount INTEGER,
                account_age_seconds INTEGER,
                transaction_count INTEGER,
                applied_at TEXT,
                status TEXT,
                risk_score REAL,
                hunger_score REAL,
                maturity_score REAL,
                narrative TEXT
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS identity_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_fingerprint TEXT,
                account_ids_json TEXT,
                total_accounts_from_device INTEGER,
                risk_score REAL,
                action_taken TEXT,
                narrative TEXT,
                timestamp TEXT
            )
        ''')

def insert_account(data):
    with get_db() as conn:
        cursor = conn.execute('''
            INSERT INTO synthetic_accounts (
                account_id, name, pan_number, aadhaar_last4, device_fingerprint,
                screen_resolution, timezone, browser_ua, form_fill_duration_ms,
                created_at, status, risk_score, device_score, entropy_score, velocity_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('account_id'), data.get('name'), data.get('pan_number'),
            data.get('aadhaar_last4'), data.get('device_fingerprint'),
            data.get('screen_resolution'), data.get('timezone'), data.get('browser_ua'),
            data.get('form_fill_duration_ms'),
            datetime.datetime.utcnow().isoformat(), data.get('status'),
            data.get('risk_score'), data.get('device_score'),
            data.get('entropy_score'), data.get('velocity_score')
        ))
        return cursor.lastrowid

def update_account_status(account_id, status):
    with get_db() as conn:
        conn.execute('UPDATE synthetic_accounts SET status = ? WHERE account_id = ?', (status, account_id))

def get_accounts_by_device(device_fingerprint):
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM synthetic_accounts WHERE device_fingerprint = ?', (device_fingerprint,)).fetchall()
        return [dict(row) for row in rows]

def get_all_accounts(limit=20):
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM synthetic_accounts ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        return [dict(row) for row in rows]

def insert_credit_application(data):
    with get_db() as conn:
        cursor = conn.execute('''
            INSERT INTO credit_applications (
                account_id, requested_amount, account_age_seconds, transaction_count,
                applied_at, status, risk_score, hunger_score, maturity_score, narrative
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('account_id'), data.get('requested_amount'), data.get('account_age_seconds'),
            data.get('transaction_count'), datetime.datetime.utcnow().isoformat(),
            data.get('status'), data.get('risk_score'), data.get('hunger_score'),
            data.get('maturity_score'), data.get('narrative')
        ))
        return cursor.lastrowid

def update_credit_status(application_id, status):
    with get_db() as conn:
        conn.execute('UPDATE credit_applications SET status = ? WHERE id = ?', (status, application_id))

def get_credit_applications(limit=20):
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM credit_applications ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        return [dict(row) for row in rows]

def insert_identity_alert(data):
    with get_db() as conn:
        conn.execute('''
            INSERT INTO identity_alerts (
                device_fingerprint, account_ids_json, total_accounts_from_device,
                risk_score, action_taken, narrative, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('device_fingerprint'), json.dumps(data.get('account_ids', [])),
            data.get('total_accounts'), data.get('risk_score'), data.get('action'),
            data.get('narrative'), datetime.datetime.utcnow().isoformat()
        ))

def get_identity_alerts(limit=50):
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM identity_alerts ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        return [dict(row) for row in rows]

def get_device_stats(device_fingerprint=None):
    with get_db() as conn:
        stats = {
            "total_accounts_created": 0,
            "quarantined": 0,
            "suspended": 0,
            "credit_applications": 0,
            "credit_rejected": 0,
            "total_credit_attempted": 0,
            "total_credit_issued": 0,
            "total_credit_blocked": 0
        }
        
        query_base = ""
        params = ()
        if device_fingerprint:
            query_base = "WHERE device_fingerprint = ?"
            params = (device_fingerprint,)
            
        stats["total_accounts_created"] = conn.execute(f'SELECT COUNT(*) FROM synthetic_accounts {query_base}', params).fetchone()[0]
        stats["quarantined"] = conn.execute(f'SELECT COUNT(*) FROM synthetic_accounts WHERE status="ALERT"').fetchone()[0]
        stats["suspended"] = conn.execute(f'SELECT COUNT(*) FROM synthetic_accounts WHERE status="BLOCKED"').fetchone()[0]
        
        ca_base = ""
        if device_fingerprint:
            ca_base = 'WHERE account_id IN (SELECT account_id FROM synthetic_accounts WHERE device_fingerprint = ?)'
        
        stats["credit_applications"] = conn.execute(f'SELECT COUNT(*) FROM credit_applications {ca_base}', params).fetchone()[0]
        stats["credit_rejected"] = conn.execute(f'SELECT COUNT(*) FROM credit_applications WHERE status="REJECTED"').fetchone()[0]
        
        att = conn.execute(f'SELECT SUM(requested_amount) FROM credit_applications {ca_base}', params).fetchone()[0]
        stats["total_credit_attempted"] = att if att else 0
        
        iss = conn.execute(f'SELECT SUM(requested_amount) FROM credit_applications WHERE status="APPROVED"').fetchone()[0]
        stats["total_credit_issued"] = iss if iss else 0
        
        blk = conn.execute(f'SELECT SUM(requested_amount) FROM credit_applications WHERE status="REJECTED"').fetchone()[0]
        stats["total_credit_blocked"] = blk if blk else 0
        
        return stats

def reset_database():
    with get_db() as conn:
        conn.execute('DELETE FROM synthetic_accounts')
        conn.execute('DELETE FROM credit_applications')
        conn.execute('DELETE FROM identity_alerts')
