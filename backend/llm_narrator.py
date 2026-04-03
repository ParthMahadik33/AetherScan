import os

import groq
from dotenv import load_dotenv


load_dotenv()
client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_threat_narrative(alert_data: dict) -> str:
    system_prompt = (
        "You are a senior SOC analyst at a FinTech security operations center.\n"
        "You write concise, actionable threat intelligence briefs.\n"
        "Always respond in 3 sentences maximum.\n"
        "Format: What is happening | Why it is dangerous | Recommended immediate action.\n"
        "Be specific with the data provided. Use technical language appropriate for a security analyst."
    )

    features = alert_data.get("features", {})
    ip = alert_data.get("ip", "unknown")
    risk_score = alert_data.get("risk_score", 0.0)
    status = alert_data.get("status", "UNKNOWN")
    attack_type = alert_data.get("attack_type", "unknown")

    user_prompt = (
        "Generate a threat brief for this alert:\n"
        f"IP: {ip}\n"
        f"Status: {status}\n"
        f"Attack Type: {attack_type}\n"
        f"Risk Score: {alert_data.get('risk_score', 0.0)}/100\n"
        f"Isolation Forest Score: {alert_data.get('iso_score', 0.0)}/100\n"
        f"LSTM Temporal Score: {alert_data.get('lstm_score', 0.0)}/100\n"
        f"Probing Score: {alert_data.get('probe_score', 0.0)}/100\n"
        f"Confidence: {alert_data.get('confidence', 0.0)}%\n"
        f"Key behavioral signals: attempt_rate_30s={features.get('attempt_rate_30s', 0.0)},\n"
        f"failure_rate={features.get('failure_rate', 0.0)},\n"
        f"inter_arrival_variance={features.get('inter_arrival_variance', 0.0)},\n"
        f"geo_velocity={features.get('geo_velocity', 0.0)},\n"
        f"keystroke_entropy={features.get('keystroke_entropy', 0.0)}"
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=200,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content
    except Exception:
        return (
            f"AetherSense detected anomalous behavior from {ip} with risk score {risk_score}/100.\n"
            f"Status: {status}. Attack type: {attack_type}.\n"
            "Immediate review and manual investigation recommended."
        )
