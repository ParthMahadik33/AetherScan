import time
import random

try:
    from . import base
except ImportError:
    import base


ATTACK_TYPE = "attack_password_spray"
TARGET_IP = "185.220.101.5"


def run():
    base.clear_stop(ATTACK_TYPE)
    event_count = 0
    while not base.should_stop(ATTACK_TYPE):
        unique_users = float(random.randint(30, 60))
        # 15% chance of finding right password for an account
        got_lucky = random.random() < 0.15

        event = {
            "ip": TARGET_IP,
            "user": "attacker_bot",
            "success": 1 if got_lucky else 0,
            "attempt_rate_30s": random.uniform(2, 4),
            "unique_users_targeted": unique_users,
            "failure_rate": 0.65 if got_lucky else 0.85,  # drops when finding valid passwords
            "inter_arrival_variance": 0.2,
            "threshold_proximity": 0.4,
            "session_duration_delta": -10.0,
            "endpoint_entropy": 0.6,
            "user_agent_consistency": 0.6,
            "geo_velocity": 0.0,
            "keystroke_entropy": 0.02,
            "baseline_deviation_7d": 0.5,
            "request_regularity": 0.9,
            "suspicion_composite": 0.75,
            "session_entropy": 0.35,
            "device_change_score": 0.15,
        }
        
        if got_lucky:
            print(f"[{event_count}] ⚠️  VALID PASSWORD FOUND for one account!")

        result = base.send_event(event)
        event_count += 1
        status = result.get("status", "ERROR")
        print(
            f"[{event_count}] {TARGET_IP} -> {status} | "
            f"risk_score: {result.get('risk_score', '?')}"
        )
        time.sleep(3)


if __name__ == "__main__":
    print(f"[+] Starting Password Spraying attack on {TARGET_IP}")
    print("[+] Press Ctrl+C to stop")
    run()
