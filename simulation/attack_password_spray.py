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
    while not base.should_stop(ATTACK_TYPE):
        failure_rate = 0.85
        event = {
            "ip": TARGET_IP,
            "user": "attacker_bot",
            "success": 1 if random.random() > failure_rate else 0,
            "attempt_rate_30s": 3.0,
            "unique_users_targeted": float(random.randint(30, 60)),
            "failure_rate": failure_rate,
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
        base.send_event(event)
        time.sleep(3)
