import time
import random

try:
    from . import base
except ImportError:
    import base


ATTACK_TYPE = "attack_synthetic_identity"
TARGET_IP = "45.33.32.156"


def run():
    base.clear_stop(ATTACK_TYPE)
    while not base.should_stop(ATTACK_TYPE):
        failure_rate = 0.3
        event = {
            "ip": TARGET_IP,
            "user": "attacker_bot",
            "success": 1 if random.random() > failure_rate else 0,
            "attempt_rate_30s": 8.0,
            "unique_users_targeted": float(random.randint(10, 20)),
            "failure_rate": failure_rate,
            "inter_arrival_variance": 0.2,
            "threshold_proximity": 0.35,
            "session_duration_delta": -99.0,
            "endpoint_entropy": 0.65,
            "user_agent_consistency": 0.4,
            "geo_velocity": 20.0,
            "keystroke_entropy": 0.0,
            "baseline_deviation_7d": 0.65,
            "request_regularity": 0.85,
            "suspicion_composite": 0.7,
            "session_entropy": 0.55,
            "device_change_score": random.uniform(0.6, 0.9),
        }
        base.send_event(event)
        time.sleep(1.5)
