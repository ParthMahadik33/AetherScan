import numpy as np
import pandas as pd
import pickle
import os

import torch
import torch.nn as nn
import torch.optim as optim

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


DATA_FILE = "models/normal_traffic.csv"
SEQUENCE_LENGTH = 20
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


def train_isolation_forest(data_df: pd.DataFrame):
    X = data_df[FEATURES].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso_forest = IsolationForest(
        n_estimators=200,
        contamination=0.01,
        random_state=42,
    )
    iso_forest.fit(X_scaled)

    os.makedirs("models", exist_ok=True)
    with open("models/iso_scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    with open("models/iso_forest.pkl", "wb") as f:
        pickle.dump(iso_forest, f)

    print("Isolation Forest trained and saved")


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


def train_lstm_autoencoder(data_df: pd.DataFrame):
    X = data_df[FEATURES].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Build sequences of length SEQUENCE_LENGTH using non-overlapping windows.
    num_rows = X_scaled.shape[0]
    seqs = []
    for start in range(0, num_rows - SEQUENCE_LENGTH + 1, SEQUENCE_LENGTH):
        window = X_scaled[start : start + SEQUENCE_LENGTH]
        seqs.append(window)

    if not seqs:
        raise ValueError(
            f"Not enough rows in {DATA_FILE} to build sequences of length "
            f"{SEQUENCE_LENGTH}."
        )

    X_seq = np.stack(seqs, axis=0)  # (num_sequences, 20, 15)
    X_tensor = torch.tensor(X_seq, dtype=torch.float32)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = LSTMAutoencoder(input_size=15, hidden_size=32, num_layers=2).to(device)
    model.train()

    dataset = torch.utils.data.TensorDataset(X_tensor, X_tensor)
    loader = torch.utils.data.DataLoader(dataset, batch_size=256, shuffle=True)

    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    for epoch in range(30):
        epoch_loss = 0.0
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)

            optimizer.zero_grad()
            recon = model(batch_x)
            loss = criterion(recon, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()

        if (epoch + 1) % 5 == 0:
            avg_loss = epoch_loss / max(1, len(loader))
            print(f"Epoch {epoch+1}/{30}, Loss: {avg_loss:.6f}")

    model.eval()

    # Compute per-sequence MSE reconstruction error.
    with torch.no_grad():
        X_seq_device = X_tensor.to(device)
        recon = model(X_seq_device)
        per_seq_mse = ((recon - X_seq_device) ** 2).mean(dim=(1, 2)).detach().cpu().numpy()

    p95 = float(np.percentile(per_seq_mse, 95))
    p99 = float(np.percentile(per_seq_mse, 99))

    os.makedirs("models", exist_ok=True)
    thresholds_path = "models/lstm_thresholds.npy"
    np.save(thresholds_path, np.array([p95, p99], dtype=np.float32))

    torch.save(model.state_dict(), "models/lstm_autoencoder.pt")

    print("LSTM Autoencoder trained and saved")
    print(f"p95 threshold: {p95}, p99 threshold: {p99}")


def main():
    data_df = pd.read_csv(DATA_FILE)
    train_isolation_forest(data_df)
    train_lstm_autoencoder(data_df)


if __name__ == "__main__":
    main()

