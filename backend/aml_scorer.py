import dateutil.parser
import statistics
import datetime
from collections import defaultdict

# In-memory state per account
transaction_history = defaultdict(list)
# Escrow queue holds items as { transaction_id: { ..., account_id, amount, ... } }
escrow_queue = {}
blocked_accounts = set()

def reset_state():
    transaction_history.clear()
    escrow_queue.clear()
    blocked_accounts.clear()

def _parse_time(timestamp):
    if isinstance(timestamp, (int, float)):
        return datetime.datetime.utcfromtimestamp(timestamp)
    elif isinstance(timestamp, str):
        return dateutil.parser.isoparse(timestamp)
    elif isinstance(timestamp, datetime.datetime):
        return timestamp
    return datetime.datetime.utcnow()

def score_transaction(account_id, amount, recipient_id, timestamp):
    # Ensure amount is float for variance math
    amount = float(amount)
    dt = _parse_time(timestamp)
    now_ts = dt.timestamp()
    
    account_txns = transaction_history[account_id]
    
    # Calculate Velocity Score (Transactions in last 60s)
    last_60s = [tx for tx in account_txns if now_ts - _parse_time(tx["timestamp"]).timestamp() <= 60]
    velocity_count = len(last_60s) + 1  # including current
    if velocity_count == 1:
        v_score = 5
    elif velocity_count == 2:
        v_score = 15
    elif velocity_count == 3:
        v_score = 40
    elif velocity_count == 4:
        v_score = 65
    elif velocity_count == 5:
        v_score = 85
    else:
        v_score = 100

    # Calculate Threshold Proximity Score
    p_score = 0
    if 9000 <= amount <= 9999:
        p_score += 35
        
    if len(account_txns) + 1 >= 3:
        p_score += 25
        
    recent_5 = [amount] + [tx["amount"] for tx in account_txns[-4:]]
    if len(recent_5) >= 2:
        variance = statistics.variance(recent_5) if len(recent_5) > 1 else 0
        if variance < 500:
            p_score += 20
    
    if str(amount).startswith('9'):
        p_score += 20
        
    p_score = min(p_score, 100)
    
    # Calculate Fan-Out Score (Unique recipients in last 10 mins)
    last_10m = [tx for tx in account_txns if now_ts - _parse_time(tx["timestamp"]).timestamp() <= 600]
    recipients_10m = set(tx["recipient_id"] for tx in last_10m)
    recipients_10m.add(recipient_id) # include current
    unique_recipients = len(recipients_10m)
    
    if unique_recipients <= 2:
        f_score = 0
    elif unique_recipients <= 4:
        f_score = 40
    elif unique_recipients <= 7:
        f_score = 70
    else:
        f_score = 100
        
    # Calculate Cumulative Amount Score (Outflow in last 10 mins)
    total_outflow = sum(tx["amount"] for tx in last_10m) + amount
    if total_outflow < 20000:
        c_score = 0
    elif total_outflow <= 50000:
        c_score = 30
    elif total_outflow <= 100000:
        c_score = 60
    else:
        c_score = 100
        
    # Composite Score
    composite = (v_score * 0.30) + (p_score * 0.30) + (f_score * 0.25) + (c_score * 0.15)
    composite = round(composite, 2)
    
    # Determine Status & Action
    if composite <= 30:
        status, action = "NORMAL", "complete"
    elif composite <= 55:
        status, action = "MONITORING", "complete"
    elif composite <= 74:
        status, action = "ALERT", "hold"
    else:
        status, action = "BLOCKED", "reverse_all"
        blocked_accounts.add(account_id)
        
    # If account is already blocked, override
    if account_id in blocked_accounts and action != "reverse_all":
        status, action = "BLOCKED", "reverse_all"
        composite = 100

    # Save to history AFTER scoring
    transaction_history[account_id].append({
        "timestamp": dt.isoformat(),
        "amount": amount,
        "recipient_id": recipient_id,
        "status": status,
        "composite": composite
    })

    return {
        "risk_score": composite,
        "velocity_score": v_score,
        "proximity_score": p_score,
        "fanout_score": f_score,
        "cumulative_score": c_score,
        "status": status,
        "action": action
    }
