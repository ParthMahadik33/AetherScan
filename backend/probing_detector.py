import time
from collections import defaultdict

import numpy as np


ip_windows = defaultdict(list)
ip_timing = defaultdict(list)


def check_probing(ip, features_dict):
    ip_windows[ip].append(features_dict["attempt_rate_30s"])
    ip_timing[ip].append(time.time())

    ip_windows[ip] = ip_windows[ip][-10:]
    ip_timing[ip] = ip_timing[ip][-10:]

    if len(ip_windows[ip]) < 5:
        return {"is_probing": False, "probe_score": 0.0}

    window = ip_windows[ip]
    target = features_dict["threshold_proximity"] * 10
    close_count = sum(1 for value in window if abs(value - target) <= 2)
    probing_ratio = close_count / len(window)

    timings = ip_timing[ip]
    gaps = np.diff(timings)
    if len(gaps) == 0:
        timing_std = 0.0
    else:
        timing_std = float(np.std(gaps))

    timing_regularity = max(0.0, 1.0 - (timing_std / 1.5))

    probe_score = (probing_ratio * 0.6 + timing_regularity * 0.4) * 100.0
    is_probing = probe_score > 30.0

    return {"is_probing": bool(is_probing), "probe_score": float(probe_score)}
