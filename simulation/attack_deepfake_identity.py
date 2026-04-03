import time
import random

try:
    from . import base
except ImportError:
    import base


ATTACK_TYPE = "attack_deepfake_identity"
TARGET_IP = "162.158.88.1"


def run():
    base.clear_stop(ATTACK_TYPE)
    event_count = 0
    while not base.should_stop(ATTACK_TYPE):
        failure_rate = 0.2
        event = {
            "ip": TARGET_IP,
            "user": "attacker_bot",
            "success": 1 if random.random() > failure_rate else 0,
            "attempt_rate_30s": 6.0,
            "unique_users_targeted": float(random.randint(15, 25)),
            "failure_rate": failure_rate,
            "inter_arrival_variance": 0.2,
            "threshold_proximity": 0.45,
            "session_duration_delta": -99.0,
            "endpoint_entropy": 0.8,
            "user_agent_consistency": 0.35,
            "geo_velocity": 30.0,
            "keystroke_entropy": 0.0,
            "baseline_deviation_7d": 0.8,
            "request_regularity": 0.85,
            "suspicion_composite": 0.85,
            "session_entropy": 0.75,
            "device_change_score": random.uniform(0.7, 0.95),
        }
        result = base.send_event(event)
        event_count += 1
        status = result.get("status", "ERROR")
        print(
            f"[{event_count}] {TARGET_IP} -> {status} | "
            f"risk_score: {result.get('risk_score', '?')}"
        )
        time.sleep(1.5)


if __name__ == "__main__":
    print(f"[+] Starting Deepfake Identity attack on {TARGET_IP}")
    print("[+] Press Ctrl+C to stop")
    run()
