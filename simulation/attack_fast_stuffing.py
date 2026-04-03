import time
import random

try:
    from . import base
except ImportError:
    import base


ATTACK_TYPE = "attack_fast_stuffing"
TARGET_IP = "203.0.113.47"


def run():
    base.clear_stop(ATTACK_TYPE)
    while not base.should_stop(ATTACK_TYPE):
        failure_rate = 0.95
        event = {
            "ip": TARGET_IP,
            "user": "attacker_bot",
            "success": 1 if random.random() > failure_rate else 0,
            "attempt_rate_30s": 45.0,
            "unique_users_targeted": 25.0,
            "failure_rate": failure_rate,
            "inter_arrival_variance": 0.3,
            "threshold_proximity": 0.9,
            "session_duration_delta": -20.0,
            "endpoint_entropy": 0.75,
            "user_agent_consistency": 0.5,
            "geo_velocity": 0.0,
            "keystroke_entropy": 0.01,
            "baseline_deviation_7d": 0.6,
            "request_regularity": 0.95,
            "suspicion_composite": 0.9,
            "session_entropy": 0.3,
            "device_change_score": 0.2,
        }
        base.send_event(event)
        time.sleep(0.5)
