import time
import random

try:
    from . import base
except ImportError:
    import base


ATTACK_TYPE = "attack_ai_adaptive_bot"
TARGET_IP = "77.247.108.9"


def run():
    base.clear_stop(ATTACK_TYPE)
    event_count = 0
    state = {
        "attempt_rate_30s": 5.0,
        "unique_users_targeted": 6.0,
        "failure_rate": 0.5,
        "threshold_proximity": 0.35,
        "session_duration_delta": -15.0,
        "endpoint_entropy": 0.65,
        "user_agent_consistency": 0.55,
        "geo_velocity": 25.0,
        "keystroke_entropy": 0.08,
        "baseline_deviation_7d": 0.2,
        "request_regularity": 0.7,
        "suspicion_composite": 0.5,
        "session_entropy": 0.5,
        "device_change_score": 0.25,
    }
    adjustable = [
        "attempt_rate_30s",
        "failure_rate",
        "threshold_proximity",
        "endpoint_entropy",
        "user_agent_consistency",
        "keystroke_entropy",
        "request_regularity",
    ]
    while not base.should_stop(ATTACK_TYPE):
        event_count += 1
        if event_count % 5 == 0:
            for name in random.sample(adjustable, 3):
                state[name] = max(0.0, min(1.0, state[name] + random.choice([-0.1, 0.1])))
        state["baseline_deviation_7d"] = min(1.0, state["baseline_deviation_7d"] + 0.05)
        event = {
            "ip": TARGET_IP,
            "user": "attacker_bot",
            "success": 1 if random.random() > state["failure_rate"] else 0,
            "attempt_rate_30s": state["attempt_rate_30s"],
            "unique_users_targeted": state["unique_users_targeted"],
            "failure_rate": state["failure_rate"],
            "inter_arrival_variance": random.uniform(0.1, 0.5),
            "threshold_proximity": state["threshold_proximity"],
            "session_duration_delta": state["session_duration_delta"],
            "endpoint_entropy": state["endpoint_entropy"],
            "user_agent_consistency": state["user_agent_consistency"],
            "geo_velocity": state["geo_velocity"],
            "keystroke_entropy": state["keystroke_entropy"],
            "baseline_deviation_7d": state["baseline_deviation_7d"],
            "request_regularity": state["request_regularity"],
            "suspicion_composite": state["suspicion_composite"],
            "session_entropy": state["session_entropy"],
            "device_change_score": state["device_change_score"],
        }
        base.send_event(event)
        time.sleep(2)
