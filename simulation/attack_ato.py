import time
import random

try:
    from . import base
except ImportError:
    import base


ATTACK_TYPE = "attack_ato"
TARGET_IP = "103.21.244.8"


def run():
    base.clear_stop(ATTACK_TYPE)
    event_count = 0
    while not base.should_stop(ATTACK_TYPE):
        failure_rate = 0.1
        event = {
            "ip": TARGET_IP,
            "user": "attacker_bot",
            "success": 1 if random.random() > failure_rate else 0,
            "attempt_rate_30s": 2.0,
            "unique_users_targeted": 1.0,
            "failure_rate": failure_rate,
            "inter_arrival_variance": 0.4,
            "threshold_proximity": 0.35,
            "session_duration_delta": -15.0,
            "endpoint_entropy": 0.65,
            "user_agent_consistency": 0.1,
            "geo_velocity": 9500.0,
            "keystroke_entropy": 0.4,
            "baseline_deviation_7d": 0.85,
            "request_regularity": 0.7,
            "suspicion_composite": 0.8,
            "session_entropy": 0.55,
            "device_change_score": 0.9,
        }
        result = base.send_event(event)
        event_count += 1
        status = result.get("status", "ERROR")
        print(
            f"[{event_count}] {TARGET_IP} -> {status} | "
            f"risk_score: {result.get('risk_score', '?')}"
        )
        time.sleep(1)


if __name__ == "__main__":
    print(f"[+] Starting ATO Impossible Travel attack on {TARGET_IP}")
    print("[+] Press Ctrl+C to stop")
    run()
