import time
import random

try:
    from . import base
except ImportError:
    import base


ATTACK_TYPE = "attack_slow_mimicry"
TARGET_IP = "198.51.100.23"


def run():
    base.clear_stop(ATTACK_TYPE)
    while not base.should_stop(ATTACK_TYPE):
        failure_rate = 0.7
        event = {
            "ip": TARGET_IP,
            "user": "attacker_bot",
            "success": 1 if random.random() > failure_rate else 0,
            "attempt_rate_30s": 1.0,
            "unique_users_targeted": 2.0,
            "failure_rate": failure_rate,
            "inter_arrival_variance": 0.15,
            "threshold_proximity": 0.3,
            "session_duration_delta": 0.0,
            "endpoint_entropy": 0.5,
            "user_agent_consistency": 0.9,
            "geo_velocity": random.uniform(0, 5),
            "keystroke_entropy": random.uniform(0.6, 0.8),
            "baseline_deviation_7d": 0.25,
            "request_regularity": 0.8,
            "suspicion_composite": 0.4,
            "session_entropy": 0.45,
            "device_change_score": 0.12,
        }
        base.send_event(event)
        time.sleep(random.uniform(35, 45))
