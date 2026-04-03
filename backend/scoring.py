import numpy as np
import pickle
import torch
import torch.nn as nn
import os
from collections import deque


FEATURES = [
    "attempt_rate_30s",
    "unique_users_targeted",
    "failure_rate",
    "inter_arrival_variance",
    "threshold_proximity",
    "session_duration_delta",
    "endpoint_entropy",
    "user_agent_consistency",
    "geo_velocity",
    "keystroke_entropy",
    "baseline_deviation_7d",
    "request_regularity",
    "suspicion_composite",
    "session_entropy",
    "device_change_score",
]
SEQUENCE_LENGTH = 20
ISO_WEIGHT = 0.45
LSTM_WEIGHT = 0.35
PROBE_WEIGHT = 0.20


class LSTMAutoencoder(nn.Module):
    def __init__(self, input_size=15, hidden_size=32, num_layers=2):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.encoder = nn.LSTM(
            input_size,
            hidden_size,
            num_layers,
            batch_first=True,
        )
        self.decoder = nn.LSTM(
            hidden_size,
            hidden_size,
            num_layers,
            batch_first=True,
        )
        self.output_layer = nn.Linear(hidden_size, input_size)

    def forward(self, x):
        # Encode input sequence.
        _, (h_n, _) = self.encoder(x)
        # Take last layer's hidden state: (batch, hidden_size)
        last_hidden = h_n[-1]
        # Repeat across the sequence length.
        seq_len = x.size(1)
        repeated = last_hidden.unsqueeze(1).repeat(1, seq_len, 1)

        decoded, _ = self.decoder(repeated)
        reconstruction = self.output_layer(decoded)
        return reconstruction


BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")

with open(os.path.join(MODELS_DIR, "iso_scaler.pkl"), "rb") as _f:
    iso_scaler = pickle.load(_f)
with open(os.path.join(MODELS_DIR, "iso_forest.pkl"), "rb") as _f:
    iso_forest = pickle.load(_f)

lstm_model = LSTMAutoencoder(input_size=15, hidden_size=32, num_layers=2)
lstm_state = torch.load(
    os.path.join(MODELS_DIR, "lstm_autoencoder.pt"),
    map_location="cpu",
)
lstm_model.load_state_dict(lstm_state)
lstm_model.eval()

lstm_thresholds = np.load(os.path.join(MODELS_DIR, "lstm_thresholds.npy"))
p95 = float(lstm_thresholds[0])
p99 = float(lstm_thresholds[1])

print("AetherSense models loaded successfully")


ip_sequences = {}


def score_isolation_forest(features_dict):
    vector = np.array([features_dict[name] for name in FEATURES], dtype=np.float32).reshape(1, -1)
    scaled = iso_scaler.transform(vector)
    raw_score = float(iso_forest.decision_function(scaled)[0])

    normalized = 100.0 * (0.1 - raw_score) / (0.1 - (-0.2))
    normalized = float(np.clip(normalized, 0.0, 100.0))
    return normalized


def score_lstm(ip, features_dict):
    if ip not in ip_sequences:
        ip_sequences[ip] = deque(maxlen=SEQUENCE_LENGTH)

    current_vector = [features_dict[name] for name in FEATURES]
    ip_sequences[ip].append(current_vector)

    if len(ip_sequences[ip]) < 5:
        return 0.0

    seq = list(ip_sequences[ip])
    if len(seq) < SEQUENCE_LENGTH:
        pad_count = SEQUENCE_LENGTH - len(seq)
        seq = [seq[0]] * pad_count + seq

    seq_array = np.array(seq, dtype=np.float32)
    seq_scaled = iso_scaler.transform(seq_array)
    input_tensor = torch.tensor(seq_scaled, dtype=torch.float32).unsqueeze(0)

    with torch.no_grad():
        recon = lstm_model(input_tensor)
        mse = float(torch.mean((recon - input_tensor) ** 2).item())

    if mse <= p95:
        return 0.0
    if mse >= p99:
        return 100.0

    normalized = 100.0 * (mse - p95) / (p99 - p95)
    normalized = float(np.clip(normalized, 0.0, 100.0))
    return normalized


def compute_risk_score(ip, features_dict, probe_score=0.0):
    iso_score = score_isolation_forest(features_dict)
    lstm_score = score_lstm(ip, features_dict)

    risk_score = (
        (iso_score * ISO_WEIGHT)
        + (lstm_score * LSTM_WEIGHT)
        + (float(probe_score) * PROBE_WEIGHT)
    )
    risk_score = float(np.clip(risk_score, 0.0, 100.0))

    if risk_score >= 85:
        status = "BLOCKED"
    elif risk_score >= 70:
        status = "ALERT"
    elif risk_score >= 50:
        status = "MONITORING"
    else:
        status = "NORMAL"

    confidence = round(min(100.0, risk_score + 10.0), 1)

    return {
        "ip": ip,
        "risk_score": risk_score,
        "iso_score": iso_score,
        "lstm_score": lstm_score,
        "probe_score": float(probe_score),
        "confidence": confidence,
        "status": status,
    }
