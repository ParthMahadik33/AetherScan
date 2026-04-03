import time
import random

try:
    from . import base
except ImportError:
    import base


ATTACK_TYPE = "attack_zero_day"
TARGET_IP = "192.0.2.100"


def run():
    base.clear_stop(ATTACK_TYPE)
    while not base.should_stop(ATTACK_TYPE):
        failure_rate = 0.2
        event = {
            "ip": TARGET_IP,
            "user": "attacker_bot",
            "success": 1 if random.random() > failure_rate else 0,
            "attempt_rate_30s": 7.0,
            "unique_users_targeted": 4.0,
            "failure_rate": failure_rate,
            "inter_arrival_variance": 0.001,
            "threshold_proximity": 0.6,
            "session_duration_delta": -99.0,
            "endpoint_entropy": 0.98,
            "user_agent_consistency": 0.4,
            "geo_velocity": 40.0,
            "keystroke_entropy": 0.04,
            "baseline_deviation_7d": 0.9,
            "request_regularity": 0.99,
            "suspicion_composite": 0.95,
            "session_entropy": 0.99,
            "device_change_score": 0.3,
        }
        base.send_event(event)
        time.sleep(1)
