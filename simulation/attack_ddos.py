import time
import random

try:
    from . import base
except ImportError:
    import base


ATTACK_TYPE = "attack_ddos"
TARGET_IP = "10.0.0.1-10.0.0.20"


def run():
    base.clear_stop(ATTACK_TYPE)
    current = 1
    event_count = 0
    while not base.should_stop(ATTACK_TYPE):
        ip = f"10.0.0.{current}"
        current = 1 if current >= 20 else current + 1
        failure_rate = 0.6
        event = {
            "ip": ip,
            "user": "attacker_bot",
            "success": 1 if random.random() > failure_rate else 0,
            "attempt_rate_30s": 50.0,
            "unique_users_targeted": 1.0,
            "failure_rate": failure_rate,
            "inter_arrival_variance": 0.01,
            "threshold_proximity": 0.5,
            "session_duration_delta": -30.0,
            "endpoint_entropy": 0.7,
            "user_agent_consistency": 0.9,
            "geo_velocity": 0.0,
            "keystroke_entropy": 0.05,
            "baseline_deviation_7d": 0.8,
            "request_regularity": 1.0,
            "suspicion_composite": 0.9,
            "session_entropy": 0.5,
            "device_change_score": 0.1,
        }
        result = base.send_event(event)
        event_count += 1
        status = result.get("status", "ERROR")
        print(
            f"[{event_count}] {ip} -> {status} | "
            f"risk_score: {result.get('risk_score', '?')}"
        )
        time.sleep(0.2)


if __name__ == "__main__":
    print(f"[+] Starting DDoS Flood attack (rotating {TARGET_IP})")
    print("[+] Press Ctrl+C to stop")
    run()
