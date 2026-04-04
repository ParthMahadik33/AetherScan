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
    event_count = 0
    while not base.should_stop(ATTACK_TYPE):
        # Gradual escalation — starts legitimate, geo_velocity reveals hijack
        if event_count < 5:
            # Phase 1: looks like normal login with valid credentials
            geo_velocity = 20.0
            session_duration_delta = -5.0
            user_agent_consistency = 0.85
            baseline_deviation_7d = 0.1
            suspicion_composite = 0.15
            device_change_score = 0.1
        elif event_count < 10:
            # Phase 2: impossible travel detected
            geo_velocity = 9500.0
            session_duration_delta = -50.0
            user_agent_consistency = 0.2
            baseline_deviation_7d = 0.6
            suspicion_composite = 0.6
            device_change_score = 0.7
        else:
            # Phase 3: full hijack behavioral signature
            geo_velocity = 9500.0
            session_duration_delta = -95.0
            user_agent_consistency = 0.1
            baseline_deviation_7d = 0.8
            suspicion_composite = 0.85
            device_change_score = 0.95

        failure_rate = 0.05
        event = {
            "ip": TARGET_IP,
            "user": "victim_user_account",
            "success": 1 if random.random() > failure_rate else 0,
            "attempt_rate_30s": 2.0,
            "unique_users_targeted": 1.0,
            "failure_rate": failure_rate,
            "inter_arrival_variance": 0.3,
            "threshold_proximity": 0.4,
            "session_duration_delta": session_duration_delta,
            "endpoint_entropy": 0.7,
            "user_agent_consistency": user_agent_consistency,
            "geo_velocity": geo_velocity,
            "keystroke_entropy": 0.35,
            "baseline_deviation_7d": baseline_deviation_7d,
            "request_regularity": 0.6,
            "suspicion_composite": suspicion_composite,
            "session_entropy": 0.6,
            "device_change_score": device_change_score,
        }
        result = base.send_event(event)
        event_count += 1
        status = result.get("status", "ERROR")
        risk = result.get("risk_score", "?")

        # Show phase label
        phase = "Phase 1 - Valid login" if event_count <= 5 else \
                "Phase 2 - Impossible travel" if event_count <= 10 else \
                "Phase 3 - Hijack confirmed"

        print(f"[{event_count:2d}] {TARGET_IP} -> {status} | Risk: {risk} | {phase}")
        time.sleep(1)


if __name__ == "__main__":
    print(f"[+] Starting Session Hijacking attack on {TARGET_IP}")
    print("[+] Press Ctrl+C to stop")
    run()
