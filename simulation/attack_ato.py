import time
import random

try:
    from . import base
except ImportError:
    import base

ATTACK_TYPE = "attack_ato"
VICTIM_IP = "103.21.244.8"    # Mumbai — legitimate victim
ATTACKER_IP = "185.220.101.5" # London — attacker with stolen creds

NORMAL_PHASE_EVENTS = 3  # how many normal events before takeover

def run():
    base.clear_stop(ATTACK_TYPE)
    event_count = 0

    # Phase 1 — Victim logs in normally from Mumbai
    print("\n[Phase 1] Victim logging in normally from Mumbai...")
    for _ in range(NORMAL_PHASE_EVENTS):
        if base.should_stop(ATTACK_TYPE):
            return
        event = {
            "ip": VICTIM_IP,
            "user": "john.doe@securebank.com",
            "success": 1,
            # Normal behavior — no travel, same device, consistent browser
            "attempt_rate_30s": 1.0,
            "unique_users_targeted": 1.0,
            "failure_rate": 0.0,
            "inter_arrival_variance": 0.6,
            "threshold_proximity": 0.1,
            "session_duration_delta": 0.0,
            "endpoint_entropy": 0.3,
            "user_agent_consistency": 0.95,
            "geo_velocity": 0.0,          # not moving
            "keystroke_entropy": 0.7,     # human typing
            "baseline_deviation_7d": 0.05, # matches history
            "request_regularity": 0.4,
            "suspicion_composite": 0.05,
            "session_entropy": 0.3,
            "device_change_score": 0.05,  # same device
        }
        result = base.send_event(event)
        event_count += 1
        status = result.get("status", "ERROR")
        print(
            f"[{event_count}] {VICTIM_IP} -> {status} | "
            f"risk_score: {result.get('risk_score', '?')} | "
            f"phase: NORMAL_VICTIM"
        )
        time.sleep(1)

    # Dramatic pause before takeover
    print("\n[!] Account Takeover in progress — attacker detected in London...")
    print("[!] Mumbai → London in 3 minutes = 7,200 km/h\n")
    time.sleep(2)

    # Phase 2 — Attacker logs in from London with stolen credentials
    print("[Phase 2] Attacker attempting access from London...")
    while not base.should_stop(ATTACK_TYPE):
        event = {
            "ip": ATTACKER_IP,
            "user": "john.doe@securebank.com",  # same victim account
            "success": 1,                        # valid stolen credentials
            # Impossible travel — new device, different browser, London IP
            "attempt_rate_30s": 2.0,
            "unique_users_targeted": 1.0,
            "failure_rate": 0.0,               # credentials work — that's what makes ATO scary
            "inter_arrival_variance": 0.2,
            "threshold_proximity": 0.35,
            "session_duration_delta": -15.0,
            "endpoint_entropy": 0.65,
            "user_agent_consistency": 0.1,     # completely different browser
            "geo_velocity": 9500.0,            # Mumbai→London in 3 mins
            "keystroke_entropy": 0.4,
            "baseline_deviation_7d": 0.85,     # nothing matches victim's history
            "request_regularity": 0.7,
            "suspicion_composite": 0.8,
            "session_entropy": 0.55,
            "device_change_score": 0.9,        # brand new device
        }
        result = base.send_event(event)
        event_count += 1
        status = result.get("status", "ERROR")
        print(
            f"[{event_count}] {ATTACKER_IP} -> {status} | "
            f"risk_score: {result.get('risk_score', '?')} | "
            f"phase: ATTACKER"
        )
        time.sleep(1)


if __name__ == "__main__":
    print("[+] Starting ATO Impossible Travel attack simulation")
    print("[+] Press Ctrl+C to stop")
    run()
