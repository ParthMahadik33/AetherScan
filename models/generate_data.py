import numpy
import pandas
import random
import os

random.seed(42)
numpy.random.seed(42)

TOTAL_EVENTS = 100000
OUTPUT_FILE = "models/normal_traffic.csv"

FIXED_RANGES = {
    "threshold_proximity": (0.05, 0.30),
    "session_duration_delta": (-20, 20),
    "endpoint_entropy": (0.3, 0.7),
    "user_agent_consistency": (0.7, 1.0),
    "baseline_deviation_7d": (0.0, 0.25),
    "suspicion_composite": (0.0, 0.15),
    "session_entropy": (0.2, 0.6),
    "device_change_score": (0.0, 0.15),
}


PERSONAS = [
    {
        "name": "casual_user",
        "weight": 0.35,
        "ranges": {
            "attempt_rate_30s": (1, 3),
            "unique_users_targeted": (10, 10),
            "failure_rate": (0.05, 0.15),
            "inter_arrival_variance": (3000, 8000),
            "geo_velocity": (0, 500),
            "keystroke_entropy": (0.7, 1.0),
            **FIXED_RANGES,
        },
    },
    {
        "name": "power_user",
        "weight": 0.20,
        "ranges": {
            "attempt_rate_30s": (3, 8),
            "unique_users_targeted": (10, 10),
            "failure_rate": (0.05, 0.10),
            "inter_arrival_variance": (2000, 5000),
            "geo_velocity": (0, 300),
            "keystroke_entropy": (0.6, 0.9),
            **FIXED_RANGES,
        },
    },
    {
        "name": "mobile_user",
        "weight": 0.20,
        "ranges": {
            "attempt_rate_30s": (1, 4),
            "unique_users_targeted": (10, 10),
            "failure_rate": (0.10, 0.20),
            "inter_arrival_variance": (1000, 4000),
            "geo_velocity": (0, 200),
            "keystroke_entropy": (0.5, 0.9),
            **FIXED_RANGES,
        },
    },
    {
        "name": "developer",
        "weight": 0.10,
        "ranges": {
            "attempt_rate_30s": (5, 15),
            "unique_users_targeted": (1, 20),
            "failure_rate": (0.05, 0.15),
            "inter_arrival_variance": (500, 2000),
            "geo_velocity": (0, 100),
            "keystroke_entropy": (0.3, 0.7),
            **FIXED_RANGES,
        },
    },
    {
        "name": "enterprise_user",
        "weight": 0.10,
        "ranges": {
            "attempt_rate_30s": (2, 6),
            "unique_users_targeted": (10, 10),
            "failure_rate": (0.02, 0.08),
            "inter_arrival_variance": (1500, 4000),
            "geo_velocity": (0, 200),
            "keystroke_entropy": (0.6, 0.9),
            **FIXED_RANGES,
        },
    },
    {
        "name": "occasional_user",
        "weight": 0.05,
        "ranges": {
            "attempt_rate_30s": (1, 2),
            "unique_users_targeted": (10, 10),
            "failure_rate": (0.15, 0.35),
            "inter_arrival_variance": (4000, 10000),
            "geo_velocity": (0, 800),
            "keystroke_entropy": (0.6, 1.0),
            **FIXED_RANGES,
        },
    },
]


def generate_events():
    frames = []

    for persona in PERSONAS:
        persona_name = persona["name"]
        persona_weight = persona["weight"]
        persona_ranges = persona["ranges"]

        count = int(persona_weight * TOTAL_EVENTS)
        if count <= 0:
            continue

        attempt_rate_30s = numpy.random.uniform(
            persona_ranges["attempt_rate_30s"][0],
            persona_ranges["attempt_rate_30s"][1],
            count,
        )
        unique_users_targeted = numpy.random.uniform(
            persona_ranges["unique_users_targeted"][0],
            persona_ranges["unique_users_targeted"][1],
            count,
        )
        failure_rate = numpy.random.uniform(
            persona_ranges["failure_rate"][0],
            persona_ranges["failure_rate"][1],
            count,
        )
        inter_arrival_variance = numpy.random.uniform(
            persona_ranges["inter_arrival_variance"][0],
            persona_ranges["inter_arrival_variance"][1],
            count,
        )
        geo_velocity = numpy.random.uniform(
            persona_ranges["geo_velocity"][0],
            persona_ranges["geo_velocity"][1],
            count,
        )
        keystroke_entropy = numpy.random.uniform(
            persona_ranges["keystroke_entropy"][0],
            persona_ranges["keystroke_entropy"][1],
            count,
        )

        # Remaining features: uniform sampling within specified ranges.
        threshold_proximity = numpy.random.uniform(
            persona_ranges["threshold_proximity"][0],
            persona_ranges["threshold_proximity"][1],
            count,
        )
        session_duration_delta = numpy.random.uniform(
            persona_ranges["session_duration_delta"][0],
            persona_ranges["session_duration_delta"][1],
            count,
        )
        endpoint_entropy = numpy.random.uniform(
            persona_ranges["endpoint_entropy"][0],
            persona_ranges["endpoint_entropy"][1],
            count,
        )
        user_agent_consistency = numpy.random.uniform(
            persona_ranges["user_agent_consistency"][0],
            persona_ranges["user_agent_consistency"][1],
            count,
        )
        baseline_deviation_7d = numpy.random.uniform(
            persona_ranges["baseline_deviation_7d"][0],
            persona_ranges["baseline_deviation_7d"][1],
            count,
        )

        # Request regularity derived from sampled inter-arrival/attempt rate.
        request_regularity = inter_arrival_variance / numpy.maximum(attempt_rate_30s, 1)
        suspicion_composite = numpy.random.uniform(
            persona_ranges["suspicion_composite"][0],
            persona_ranges["suspicion_composite"][1],
            count,
        )
        session_entropy = numpy.random.uniform(
            persona_ranges["session_entropy"][0],
            persona_ranges["session_entropy"][1],
            count,
        )
        device_change_score = numpy.random.uniform(
            persona_ranges["device_change_score"][0],
            persona_ranges["device_change_score"][1],
            count,
        )

        # Add small Gaussian noise to each feature, then clip to valid range.
        attempt_rate_30s = numpy.clip(
            attempt_rate_30s + numpy.random.normal(0, 0.02, count), 0, 1
        )
        unique_users_targeted = numpy.clip(
            unique_users_targeted + numpy.random.normal(0, 0.02, count), 0, 1
        )
        failure_rate = numpy.clip(failure_rate + numpy.random.normal(0, 0.02, count), 0, 1)
        inter_arrival_variance = numpy.clip(
            inter_arrival_variance + numpy.random.normal(0, 0.02, count), 0, 1
        )
        threshold_proximity = numpy.clip(
            threshold_proximity + numpy.random.normal(0, 0.02, count), 0, 1
        )
        session_duration_delta = numpy.clip(
            session_duration_delta + numpy.random.normal(0, 0.02, count), -20, 20
        )
        endpoint_entropy = numpy.clip(
            endpoint_entropy + numpy.random.normal(0, 0.02, count), 0, 1
        )
        user_agent_consistency = numpy.clip(
            user_agent_consistency + numpy.random.normal(0, 0.02, count), 0, 1
        )
        geo_velocity = numpy.clip(geo_velocity + numpy.random.normal(0, 0.02, count), 0, 1)
        keystroke_entropy = numpy.clip(
            keystroke_entropy + numpy.random.normal(0, 0.02, count), 0, 1
        )
        baseline_deviation_7d = numpy.clip(
            baseline_deviation_7d + numpy.random.normal(0, 0.02, count), 0, 1
        )
        request_regularity = numpy.clip(
            request_regularity + numpy.random.normal(0, 0.02, count), 0, 1
        )
        suspicion_composite = numpy.clip(
            suspicion_composite + numpy.random.normal(0, 0.02, count), 0, 1
        )
        session_entropy = numpy.clip(
            session_entropy + numpy.random.normal(0, 0.02, count), 0, 1
        )
        device_change_score = numpy.clip(
            device_change_score + numpy.random.normal(0, 0.02, count), 0, 1
        )

        df = pandas.DataFrame(
            {
                "attempt_rate_30s": attempt_rate_30s,
                "unique_users_targeted": unique_users_targeted,
                "failure_rate": failure_rate,
                "inter_arrival_variance": inter_arrival_variance,
                "threshold_proximity": threshold_proximity,
                "session_duration_delta": session_duration_delta,
                "endpoint_entropy": endpoint_entropy,
                "user_agent_consistency": user_agent_consistency,
                "geo_velocity": geo_velocity,
                "keystroke_entropy": keystroke_entropy,
                "baseline_deviation_7d": baseline_deviation_7d,
                "request_regularity": request_regularity,
                "suspicion_composite": suspicion_composite,
                "session_entropy": session_entropy,
                "device_change_score": device_change_score,
                "persona": persona_name,
            }
        )
        frames.append(df)

    combined = pandas.concat(frames, ignore_index=True)
    combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)
    return combined


def main():
    df = generate_events()
    output_dir = os.path.dirname(OUTPUT_FILE)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Generated {len(df)} events saved to normal_traffic.csv")


if __name__ == "__main__":
    main()

