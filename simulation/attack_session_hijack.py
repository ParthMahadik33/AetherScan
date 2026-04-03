import time
import random

try:
    from . import base
except ImportError:
    import base


ATTACK_TYPE = "attack_session_hijack"
TARGET_IP = "94.102.49.18"


def run():
    base.clear_stop(ATTACK_TYPE)
    while not base.should_stop(ATTACK_TYPE):
        failure_rate = 0.05
        event = {
            "ip": TARGET_IP,
            "user": "attacker_bot",
            "success": 1 if random.random() > failure_rate else 0,
            "attempt_rate_30s": 2.0,
            "unique_users_targeted": 2.0,
            "failure_rate": failure_rate,
            "inter_arrival_variance": 0.3,
            "threshold_proximity": 0.4,
            "session_duration_delta": -95.0,
            "endpoint_entropy": 0.7,
            "user_agent_consistency": 0.1,
            "geo_velocity": 8000.0,
            "keystroke_entropy": 0.35,
            "baseline_deviation_7d": 0.8,
            "request_regularity": 0.6,
            "suspicion_composite": 0.85,
            "session_entropy": 0.6,
            "device_change_score": 0.95,
        }
        base.send_event(event)
        time.sleep(1)
