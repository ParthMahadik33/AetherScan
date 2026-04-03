import importlib
import threading


ATTACK_MAP = {
    "fast_stuffing": "simulation.attack_fast_stuffing",
    "password_spray": "simulation.attack_password_spray",
    "slow_mimicry": "simulation.attack_slow_mimicry",
    "probing_discovery": "simulation.attack_probing_discovery",
    "ato": "simulation.attack_ato",
    "session_hijack": "simulation.attack_session_hijack",
    "synthetic_identity": "simulation.attack_synthetic_identity",
    "headless_browser": "simulation.attack_headless_browser",
    "ai_adaptive_bot": "simulation.attack_ai_adaptive_bot",
    "ddos": "simulation.attack_ddos",
    "api_scraping": "simulation.attack_api_scraping",
    "card_testing": "simulation.attack_card_testing",
    "zero_day": "simulation.attack_zero_day",
    "llm_injection": "simulation.attack_llm_injection",
    "deepfake_identity": "simulation.attack_deepfake_identity",
}


def start_attack(attack_type, active_attacks: dict):
    if attack_type in active_attacks:
        return {"status": "already_running"}

    module_path = ATTACK_MAP.get(attack_type)
    if not module_path:
        return {"status": "not_found", "attack_type": attack_type}

    module = importlib.import_module(module_path)
    module.base.clear_stop(attack_type)
    module.base.clear_stop(getattr(module, "ATTACK_TYPE", attack_type))

    active_attacks[attack_type] = {
        "thread": None,
        "events_sent": 0,
        "module": module,
    }

    def run_and_track():
        original_send = module.base.send_event

        def counted_send(features):
            result = original_send(features)
            active_attacks[attack_type]["events_sent"] += 1
            return result

        module.base.send_event = counted_send
        try:
            module.run()
        finally:
            module.base.send_event = original_send

    t = threading.Thread(target=run_and_track, daemon=True)
    active_attacks[attack_type]["thread"] = t
    t.start()
    return {"status": "started", "attack_type": attack_type}


def stop_attack(attack_type, active_attacks: dict):
    if attack_type not in active_attacks:
        return {"status": "not_running"}

    module = active_attacks[attack_type]["module"]
    module.base.set_stop(attack_type)
    module.base.set_stop(getattr(module, "ATTACK_TYPE", attack_type))
    active_attacks.pop(attack_type, None)
    return {"status": "stopped", "attack_type": attack_type}


def get_status(active_attacks: dict):
    return [
        {
            "attack_type": k,
            "events_sent": v["events_sent"],
            "alive": v["thread"].is_alive(),
        }
        for k, v in active_attacks.items()
    ]
