import requests


stop_flags = {}


def should_stop(attack_type):
    return stop_flags.get(attack_type, False)


def set_stop(attack_type):
    stop_flags[attack_type] = True


def clear_stop(attack_type):
    stop_flags[attack_type] = False


def send_event(features: dict):
    try:
        response = requests.post("http://localhost:5000/api/event", json=features, timeout=5)
        return response.json()
    except Exception:
        return {}
