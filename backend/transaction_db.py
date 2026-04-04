import sqlite3
import json
import os
from datetime import datetime

# DB initialization and connection mapping
DB_PATH = os.path.join(os.path.dirname(__file__), 'transactions.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # transactions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT,
            recipient_id TEXT,
            recipient_name TEXT,
            amount REAL,
            timestamp TEXT,
            status TEXT,
            risk_score REAL,
            velocity_score REAL,
            proximity_score REAL,
            fanout_score REAL,
            cumulative_score REAL
        )
    ''')
    # aml_alerts table
    c.execute('''
        CREATE TABLE IF NOT EXISTS aml_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT,
            risk_score REAL,
            status TEXT,
            action_taken TEXT,
            signal_breakdown TEXT,
            narrative TEXT,
            timestamp TEXT
        )
    ''')
    # escrow table
    c.execute('''
        CREATE TABLE IF NOT EXISTS escrow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER,
            account_id TEXT,
            amount REAL,
            held_at TEXT,
            released_at TEXT,
            outcome TEXT,
            FOREIGN KEY (transaction_id) REFERENCES transactions (id)
        )
    ''')
    conn.commit()
    conn.close()

def insert_transaction(data):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO transactions (
            account_id, recipient_id, recipient_name, amount, timestamp,
            status, risk_score, velocity_score, proximity_score, 
            fanout_score, cumulative_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['account_id'], data['recipient_id'], data['recipient_name'], 
        data['amount'], data['timestamp'], data['status'], data['risk_score'], 
        data['velocity_score'], data['proximity_score'], data['fanout_score'], 
        data['cumulative_score']
    ))
    last_id = c.lastrowid
    conn.commit()
    conn.close()
    return last_id

def update_transaction_status(txn_id, status):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE transactions SET status = ? WHERE id = ?', (status, txn_id))
    conn.commit()
    conn.close()

def get_transactions(account_id, limit=20):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM transactions 
        WHERE account_id = ? 
        ORDER BY id DESC LIMIT ?
    ''', (account_id, limit))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def insert_aml_alert(data):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO aml_alerts (
            account_id, risk_score, status, action_taken, 
            signal_breakdown, narrative, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['account_id'], data['risk_score'], data['status'], 
        data['action_taken'], json.dumps(data.get('signal_breakdown', {})), 
        data.get('narrative', ''), data.get('timestamp', datetime.utcnow().isoformat())
    ))
    conn.commit()
    conn.close()

def get_aml_alerts(limit=50):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM aml_alerts 
        ORDER BY id DESC LIMIT ?
    ''', (limit,))
    rows = c.fetchall()
    conn.close()
    # parse json for easier consumption
    res = []
    for row in rows:
        d = dict(row)
        if d.get('signal_breakdown'):
            try: d['signal_breakdown'] = json.loads(d['signal_breakdown'])
            except: pass
        res.append(d)
    return res

def add_to_escrow(transaction_id, account_id, amount):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO escrow (
            transaction_id, account_id, amount, held_at
        ) VALUES (?, ?, ?, ?)
    ''', (transaction_id, account_id, amount, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def resolve_escrow(account_id, outcome):
    conn = get_connection()
    c = conn.cursor()
    now_iso = datetime.utcnow().isoformat()
    # Update escrow entries
    c.execute('''
        UPDATE escrow 
        SET outcome = ?, released_at = ? 
        WHERE account_id = ? AND outcome IS NULL
    ''', (outcome, now_iso, account_id))
    
    # Also update the corresponding transactions
    c.execute('''
        UPDATE transactions 
        SET status = ? 
        WHERE account_id = ? AND status = 'HELD'
    ''', (outcome, account_id))
    
    conn.commit()
    conn.close()

def clear_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM transactions')
    c.execute('DELETE FROM aml_alerts')
    c.execute('DELETE FROM escrow')
    conn.commit()
    conn.close()
