import time
import random

try:
    from . import base
except ImportError:
    import base


ATTACK_TYPE = "attack_probing_discovery"
TARGET_IP = "172.16.254.99"


def run():
    base.clear_stop(ATTACK_TYPE)
    sequence = [10, 7, 5, 4, 3, 2, 2, 1]
    idx = 0
    while not base.should_stop(ATTACK_TYPE):
        if idx < len(sequence):
            attempt_rate = float(sequence[idx])
            failure_rate = 0.1
            threshold_proximity = 0.3
            inter_arrival_variance = 0.4
        else:
            attempt_rate = 3.0
            failure_rate = 0.2
            threshold_proximity = 0.05
            inter_arrival_variance = 0.8

        event = {
            "ip": TARGET_IP,
            "user": "attacker_bot",
            "success": 1 if random.random() > failure_rate else 0,
            "attempt_rate_30s": attempt_rate,
            "unique_users_targeted": 3.0,
            "failure_rate": failure_rate,
            "inter_arrival_variance": inter_arrival_variance,
            "threshold_proximity": threshold_proximity,
            "session_duration_delta": 1.0,
            "endpoint_entropy": 0.45,
            "user_agent_consistency": 0.85,
            "geo_velocity": 2.0,
            "keystroke_entropy": 0.65,
            "baseline_deviation_7d": 0.2,
            "request_regularity": 0.92,
            "suspicion_composite": 0.35,
            "session_entropy": 0.5,
            "device_change_score": 0.1,
        }
        base.send_event(event)
        idx += 1
        time.sleep(2)
