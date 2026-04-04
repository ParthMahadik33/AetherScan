import time
import datetime
import dateutil.parser
from collections import defaultdict

# In-memory states
device_registry = defaultdict(list)
account_registry = {}
credit_applications = {}
quarantined_accounts = set()
blocked_devices = set()

def reset_state():
    device_registry.clear()
    account_registry.clear()
    credit_applications.clear()
    quarantined_accounts.clear()
    blocked_devices.clear()

def _parse_time(timestamp):
    if isinstance(timestamp, (int, float)):
        return datetime.datetime.utcfromtimestamp(timestamp)
    elif isinstance(timestamp, str):
        return dateutil.parser.isoparse(timestamp)
    elif isinstance(timestamp, datetime.datetime):
        return timestamp
    return datetime.datetime.utcnow()

def score_account_creation(account_id, name, pan_number, aadhaar_last4, device_fingerprint,
                           form_fill_duration_ms, screen_resolution, timezone, browser_ua, timestamp):
    
    dt = _parse_time(timestamp)
    now_ts = dt.timestamp()
    
    # Update state
    device_registry[device_fingerprint].append(account_id)
    
    # Signal 1 - Device Fingerprint Collision (Weight 0.40)
    device_collision_count = len(device_registry[device_fingerprint])
    if device_collision_count == 1:
        d_score = 0
    elif device_collision_count == 2:
        d_score = 30
    elif device_collision_count == 3:
        d_score = 65
    elif device_collision_count == 4:
        d_score = 85
    else:
        d_score = 100
        
    # Signal 2 - Behavioral Entropy (Weight 0.35)
    if form_fill_duration_ms > 45000:
        e_score = 0
    elif form_fill_duration_ms >= 20000:
        e_score = 15
    elif form_fill_duration_ms >= 10000:
        e_score = 35
    elif form_fill_duration_ms >= 3000:
        e_score = 60
    elif form_fill_duration_ms >= 1000:
        e_score = 85
    else:
        e_score = 100
        
    # Signal 3 - Account Velocity Score (Weight 0.25)
    # New accounts from ANY device in last 5 mins (300 secs)
    recent_count = sum(
        1 for acc_meta in account_registry.values() 
        if now_ts - _parse_time(acc_meta["created_at"]).timestamp() <= 300
    )
    # Include current instance
    recent_count += 1
    
    if recent_count <= 2:
        v_score = 0
    elif recent_count <= 4:
        v_score = 30
    elif recent_count <= 7:
        v_score = 60
    else:
        v_score = 100
        
    # Composite Score
    composite = (d_score * 0.40) + (e_score * 0.35) + (v_score * 0.25)
    composite = round(composite, 2)
    
    # Block override
    if device_fingerprint in blocked_devices:
        composite = 100
        
    if composite <= 30:
        status, action = "NORMAL", "approve"
    elif composite <= 55:
        status, action = "MONITORING", "approve"
    elif composite <= 74:
        status, action = "ALERT", "quarantine"
        quarantined_accounts.add(account_id)
    else:
        status, action = "BLOCKED", "suspend_all"
        quarantined_accounts.add(account_id)
        blocked_devices.add(device_fingerprint)
        for act in device_registry[device_fingerprint]:
            quarantined_accounts.add(act)

    account_registry[account_id] = {
        "created_at": dt.isoformat(),
        "device_fingerprint": device_fingerprint,
        "status": status,
        "risk_score": composite,
    }

    # Generate Narrative
    narrative = ""
    if composite > 55:
        narrative = f"A high risk score of {composite} was triggered primarily due to anomalous onboarding behaviors. We observed a form fill duration of {form_fill_duration_ms}ms, which is indicative of automated bot-pasting algorithms rather than a human typed entry. Furthermore, this device fingerprint ({device_fingerprint[:8]}...) has collided across {device_collision_count} unique account applications, explicitly breaching our threshold for synthetic identity structuring."

    return {
        "risk_score": composite,
        "device_score": d_score,
        "entropy_score": e_score,
        "velocity_score": v_score,
        "status": status,
        "action": action,
        "device_collision_count": device_collision_count,
        "narrative": narrative
    }

def score_credit_application(account_id, requested_amount, account_age_seconds, transaction_count, timestamp):
    
    # Block checking
    account_meta = account_registry.get(account_id, {})
    device = account_meta.get("device_fingerprint")
    is_suspended_globally = device in blocked_devices
    
    # Signal 1 - Credit Hunger Score (Weight 0.60)
    if account_age_seconds > 3600:
        h_score = 0
    elif account_age_seconds >= 600:
        h_score = 20
    elif account_age_seconds >= 60:
        h_score = 55
    elif account_age_seconds >= 10:
        h_score = 85
    else:
        h_score = 100
        
    # Signal 2 - Account Maturity Score (Weight 0.40)
    if transaction_count >= 10:
        m_score = 0
    elif transaction_count >= 5:
        m_score = 20
    elif transaction_count >= 2:
        m_score = 50
    elif transaction_count == 1:
        m_score = 75
    else:
        m_score = 100
        
    composite = (h_score * 0.60) + (m_score * 0.40)
    composite = round(composite, 2)
    
    if account_id in quarantined_accounts or is_suspended_globally:
        composite = 100
        status, action = "REJECTED", "reject_credit"
    else:
        if composite <= 30:
            status, action = "APPROVED", "approve_credit"
        elif composite <= 55:
            status, action = "REVIEW", "manual_review"
        else:
            status, action = "REJECTED", "reject_credit"

    # Save to history
    credit_applications[account_id] = {
        "requested_amount": requested_amount,
        "status": status,
        "risk_score": composite,
        "timestamp": timestamp
    }

    narrative = ""
    if composite > 55:
        narrative = f"Credit application flagged and {status.lower()} with a score of {composite}. The profile displays a critical Credit Hunger signal, applying for an un-secured payload of {requested_amount} while only holding an account age of {account_age_seconds} seconds. Additionally, the account has an insufficient transactional maturity (0 prior records), meeting empirical thresholds for synthetic extraction."
        
    return {
        "risk_score": composite,
        "hunger_score": h_score,
        "maturity_score": m_score,
        "status": status,
        "action": action,
        "narrative": narrative
    }
