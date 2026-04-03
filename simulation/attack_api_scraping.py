import time
import random

import requests

try:
    from . import base
except ImportError:
    import base


ATTACK_TYPE = "attack_api_scraping"
TARGET_IP = "198.98.56.14"


def run():
    base.clear_stop(ATTACK_TYPE)
    sent = 0
    while not base.should_stop(ATTACK_TYPE):
        sent += 1
        failure_rate = 0.3
        event = {
            "ip": TARGET_IP,
            "user": "attacker_bot",
            "success": 1 if random.random() > failure_rate else 0,
            "attempt_rate_30s": 20.0,
            "unique_users_targeted": 2.0,
            "failure_rate": failure_rate,
            "inter_arrival_variance": 0.8,
            "threshold_proximity": 0.45,
            "session_duration_delta": -20.0,
            "endpoint_entropy": 0.99,
            "user_agent_consistency": 0.8,
            "geo_velocity": 0.0,
            "keystroke_entropy": 0.03,
            "baseline_deviation_7d": 0.7,
            "request_regularity": 0.95,
            "suspicion_composite": 0.85,
            "session_entropy": 0.95,
            "device_change_score": 0.2,
        }
        result = base.send_event(event)
        status = result.get("status", "ERROR")
        print(
            f"[{sent}] {TARGET_IP} -> {status} | "
            f"risk_score: {result.get('risk_score', '?')}"
        )
        if sent > 5:
            try:
                requests.get("http://localhost:5000/api/v1/internal/users", timeout=5)
            except Exception:
                pass
        time.sleep(0.8)


if __name__ == "__main__":
    print(f"[+] Starting API Scraping + Honeypot attack on {TARGET_IP}")
    print("[+] Press Ctrl+C to stop")
    run()
