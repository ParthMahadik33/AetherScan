# # AetherSense AI

> **Full-Spectrum FinTech Attack Detection Platform**  
> AI & FinTech Security Track — National Level Hackathon

[![Python](https://img.shields.io/badge/Python-3.9+-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.x-lightgrey)](https://flask.palletsprojects.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-LSTM-orange)](https://pytorch.org)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.1_8B-green)](https://groq.com)

---

## What Is This

AetherSense AI is a production-grade cybersecurity platform that detects real-world FinTech attacks in real time — and stops them before any financial loss occurs.

It covers three threat domains simultaneously:

| Module | Threat | Attacks Covered |
|--------|--------|-----------------|
| Module 1 | Authentication Security | 15 attack types |
| Module 2 | AML / Transaction Fraud | Smurfing / Transaction Structuring |
| Module 3 | Identity Fraud | Synthetic Identity + BNPL Fraud |

**The core demo:** Rule-based systems see nothing. AetherSense catches everything — with zero financial loss across all attack scenarios.

---

## Demo Overview

### Module 2 — Smurfing Attack
A bot breaks ₹5,00,000 into 20+ transactions of ₹9,200–₹9,900 each — always just below RBI's ₹10,000 PMLA reporting threshold. Every transaction passes a rule-based check. AetherSense detects the structuring pattern, issues provisional holds, and reverses all transactions. **Amount lost: ₹0.**

### Module 3 — Synthetic Identity Fraud
A bot creates 15 fake accounts using real-looking PANs, all from the same device, all filling KYC forms in under 1.5 seconds. Each immediately applies for ₹50,000 BNPL credit. Rule-based KYC approves every one — valid PAN format, valid account. AetherSense detects device fingerprint collision and zero behavioral entropy. **Credit issued: ₹0.**

### Module 1 — 15 Auth Attacks
Credential stuffing, slow mimicry bots, adversarial threshold probing, session hijacking, DDoS, API scraping, zero day behavioral exploits, LLM prompt injection, deepfake identity injection, and more.

---

## Quick Start

### Prerequisites
```bash
python 3.9+
pip
node (for docx generation only)
```

### Install
```bash
git clone https://github.com/ParthMahadik33/AetherScan
cd AetherScan
pip install -r requirements.txt
```

### Configure
```bash
# Create .env file
cp .env.example .env

# Add your Groq API key
GROQ_API_KEY=your_key_here
```
Get a free Groq API key at [console.groq.com](https://console.groq.com)

### Train Models (Module 1)
```bash
cd models
python generate_data.py    # generates 100k training events
python retrain_all.py      # trains Isolation Forest + LSTM
```

### Launch
```bash
# Windows
start.bat

# Mac / Linux
python backend/app.py
```

Then open in browser:

| Panel | URL | Module |
|-------|-----|--------|
| SecureBank (target) | http://localhost:5000/bank | 1 |
| Red Team Console | http://localhost:5000/attacker | 1 |
| SOC Dashboard | http://localhost:5000/dashboard | 1 |
| PayVault (AML demo) | http://localhost:5000/payvault | 2 |
| Identity Fraud Demo | http://localhost:5000/identity | 3 |

---

## Architecture

```
AetherSense AI
├── models/                         ← Trained ML models
│   ├── iso_forest.pkl              ← Isolation Forest (Module 1)
│   ├── iso_scaler.pkl              ← Fitted StandardScaler
│   ├── lstm_autoencoder.pt         ← LSTM Autoencoder weights
│   ├── lstm_thresholds.npy         ← p95/p99 MSE thresholds
│   ├── normal_traffic.csv          ← 100k training events
│   ├── generate_data.py            ← Synthetic data generator
│   └── retrain_all.py              ← Model training script
│
├── backend/
│   ├── app.py                      ← Flask main + all API endpoints
│   ├── scoring.py                  ← Module 1 ML scoring pipeline
│   ├── probing_detector.py         ← Adversarial probing logic
│   ├── honeypot.py                 ← Honeypot deception engine
│   ├── llm_narrator.py             ← Groq API threat narration
│   ├── attack_launcher.py          ← Background attack thread manager
│   ├── database.py                 ← Module 1 SQLite schema
│   ├── aml_scorer.py               ← Module 2 AML scoring engine
│   ├── transaction_db.py           ← Module 2 transaction storage
│   ├── identity_scorer.py          ← Module 3 identity fraud scoring
│   └── identity_db.py              ← Module 3 identity storage
│
├── simulation/                     ← Attack simulation scripts
│   ├── attack_fast_stuffing.py
│   ├── attack_slow_mimicry.py
│   ├── attack_probing_discovery.py
│   ├── attack_password_spray.py
│   ├── attack_card_testing.py
│   ├── attack_ato.py
│   ├── attack_session_hijack.py
│   ├── attack_api_scraping.py
│   ├── attack_headless_browser.py
│   ├── attack_ddos.py
│   ├── attack_ai_adaptive_bot.py
│   ├── attack_deepfake_identity.py
│   ├── attack_zero_day.py
│   ├── attack_llm_injection.py
│   ├── attack_synthetic_identity.py
│   └── attack_smurfing.py          ← Module 2 (new)
│
├── frontend/
│   ├── bank.html                   ← SecureBank target app
│   ├── attacker.html               ← Red Team attack console
│   ├── dashboard.html              ← Module 1 SOC dashboard
│   ├── payvault.html               ← Module 2 three-panel demo
│   └── identity_attack.html        ← Module 3 three-panel demo
│
├── .env                            ← API keys (never committed)
├── .gitignore
├── requirements.txt
└── start.bat                       ← One-click demo launcher
```

---

## ML Architecture — Module 1

### Three-Layer Detection

**Layer 1 — Isolation Forest (45% weight)**  
Trained on 100,000 synthetic login events across 6 user personas. Builds a high-dimensional map of normal behavior. Scores incoming events by how many random splits are required to isolate them — anomalous events isolate fast.

**Layer 2 — LSTM Autoencoder (35% weight)**  
Maintains a rolling window of the last 20 events per IP. Learns normal temporal sequences. Reconstruction MSE is the anomaly score — high MSE means the sequence is unlike anything in training data. This is what catches slow-and-low attacks invisible to the Isolation Forest.

**Layer 3 — Adversarial Probing Detector (20% weight)**  
Monitors threshold-proximity behavior per IP. Detects attackers mapping defenses before launching — before any attack threshold is crossed. No other system detects this.

### 15-Feature Input Vector

| Feature | Measures | Primary Signal |
|---------|----------|----------------|
| attempt_rate_30s | Requests in last 30 seconds | Fast stuffing, DDoS |
| unique_users_targeted | Distinct usernames per IP | Credential stuffing |
| failure_rate | Failed / total attempts | All credential attacks |
| inter_arrival_variance | Timing variance between requests | Bot vs human pacing |
| threshold_proximity | Distance from detection threshold | Adversarial probing |
| session_duration_delta | Deviation from user baseline | ATO, card testing |
| endpoint_entropy | Distribution across API endpoints | API scraping |
| user_agent_consistency | UA string variance per IP | Bot tooling |
| geo_velocity | Speed of location change (km/h) | Impossible travel |
| keystroke_entropy | Timing variance of form input | Bot vs human typing |
| baseline_deviation_7d | Delta from 7-day rolling normal | Adaptive baseline |
| request_regularity | Composite bot regularity signal | Bot fingerprint |
| suspicion_composite | Weighted multi-signal combination | Bot fingerprint |
| session_entropy | Entropy of endpoints per session | Session hijack |
| device_change_score | Device fingerprint deviation | ATO, synthetic identity |

### Risk Score and Response

| Score | Status | Action |
|-------|--------|--------|
| 0–49 | NORMAL | None |
| 50–69 | MONITORING | Increased logging |
| 70–84 | ALERT | CAPTCHA + LLM narration |
| 85+ | BLOCKED | IP block + session invalidation |
| Any + Probing | PROBING | Silent monitoring + evidence collection |
| Any + Honeypot | HONEYPOT | Instant block, zero ML needed |

---

## AML Detection — Module 2

### How Smurfing Works
Attacker breaks ₹5,00,000 into 50+ transactions of ₹9,200–₹9,900. Each is below RBI's ₹10,000 PMLA reporting threshold. Rule-based systems check one thing: is this above ₹10,000? No → allow. Every transaction passes.

### Four Detection Signals

| Signal | Weight | Trigger | What It Catches |
|--------|--------|---------|-----------------|
| Velocity Score | 30% | 6+ txns in 60s | Rapid-fire micro-transactions |
| Threshold Proximity | 30% | Amount ₹9,000–₹9,999 | Deliberate structuring pattern |
| Fan-Out Score | 25% | 8+ unique recipients | One source → many mule accounts |
| Cumulative Amount | 15% | ₹1,00,000+ in 10 min | Large outflow disguised as small txns |

```
Composite = (Velocity × 0.30) + (Proximity × 0.30) 
          + (Fan-Out × 0.25) + (Cumulative × 0.15)
```

### Zero Loss Architecture
Transactions don't fail — they enter a provisional hold (escrow). Money leaves the sender but never reaches the recipient. On BLOCKED, all escrow transactions reverse simultaneously. The attacker sees "Processing..." throughout and never knows they've been caught.

---

## Identity Fraud Detection — Module 3

### How Synthetic Identity Fraud Works
Bot creates 15 accounts using real-format PANs from leaked data. Each passes basic KYC — valid format. Each immediately applies for ₹50,000 BNPL credit. Total exposure: ₹7,50,000.

### Detection Signals

**Account Creation (3 signals):**

| Signal | Weight | Bot Pattern | Legitimate User |
|--------|--------|-------------|-----------------|
| Device Fingerprint Collision | 40% | 15 accounts, same device | 1 account per device |
| Behavioral Entropy | 35% | Form filled in 800ms | Form filled in 45–120 seconds |
| Account Velocity | 25% | 15 accounts in 8 minutes | 1 account, ever |

**Credit Application (3 signals):**

| Signal | Weight | Bot Pattern | Legitimate User |
|--------|--------|-------------|-----------------|
| Credit Hunger | 45% | Applies within 10 seconds | Applies after browsing |
| Account Maturity | 20% | Zero prior transactions | Some account history |
| Device Reputation | 35% | Device already flagged | Clean device |

### Combined Gate — No False Positives
A legitimate new user with a clean device who applies for credit quickly gets **REVIEW** not **REJECTED**. Only accounts where both creation score AND device reputation are high get hard rejected. This is what separates AetherSense from a system that just blocks everyone.

### Retroactive Revocation
If a device gets confirmed as fraud on Account 5, any credit approved on Accounts 1–4 from the same device is **retroactively revoked**. The fraud window closes even if some accounts slipped through.

---

## Honeypot Deception Layer

Five hidden API endpoints that no legitimate user can ever reach:

```
/api/v1/internal/users     ← user enumeration trap
/api/v1/admin/dump         ← database dump trap
/api/v1/system/config      ← system config trap
/api/v1/debug/login        ← auth bypass trap
/api/v1/hidden/export      ← data export trap
```

Three hidden form fields that legitimate browsers render invisible:
```
email_confirm    ← hidden email confirmation
phone_verify     ← hidden phone verification
bot_check        ← explicit honeypot field
```

When triggered: system returns a convincing fake 200 response with plausible data. IP is silently blocked. Attacker never knows they've been caught.

---

## API Reference

### Module 1 — Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/event` | POST | Score a login event — runs all ML models |
| `/api/alerts` | GET | Last 50 alerts |
| `/api/health` | GET | Model load status |
| `/api/clear` | GET | Reset state for fresh demo |
| `/api/attack/start` | POST | Start attack simulation |
| `/api/attack/stop` | POST | Stop attack simulation |
| `/api/attack/status` | GET | Currently running attacks |

### Module 2 — AML
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/transaction` | POST | Score a payment transaction |
| `/api/transactions/<id>` | GET | Transaction history for account |
| `/api/aml/alerts` | GET | AML alert log |
| `/api/aml/account/<id>` | GET | Account status + balance |
| `/api/aml/reset` | POST | Reset AML state |

### Module 3 — Identity
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/identity/create-account` | POST | Score account creation |
| `/api/identity/apply-credit` | POST | Score credit application |
| `/api/identity/accounts` | GET | All accounts + status |
| `/api/identity/alerts` | GET | Identity fraud alerts |
| `/api/identity/stats` | GET | Totals — credit attempted vs issued |
| `/api/identity/reset` | POST | Reset identity state |

---

## Running Individual Attack Simulations

```bash
# Module 1 — Auth attacks (via UI or directly)
python simulation/attack_slow_mimicry.py
python simulation/attack_probing_discovery.py
python simulation/attack_fast_stuffing.py

# Module 2 — Smurfing
python simulation/attack_smurfing.py
python simulation/attack_smurfing.py --delay 2.5   # slower for demo
python simulation/attack_smurfing.py --mode manual  # step by step

# Module 3 — Synthetic Identity
python simulation/attack_synthetic_identity.py
python simulation/attack_synthetic_identity.py --delay 1.5
python simulation/attack_synthetic_identity.py --mode manual
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| ML Models | scikit-learn IsolationForest + PyTorch LSTM | Behavioral anomaly + temporal sequence detection |
| AML Scoring | Python statistical logic | Velocity, proximity, fan-out, cumulative detection |
| Identity Scoring | Python statistical logic | Device collision, entropy, credit hunger |
| LLM | Groq API — LLaMA 3.1 8B Instant | Auto-generated threat narratives |
| Backend | Flask + Flask-SocketIO + Flask-CORS | REST + WebSocket real-time streaming |
| Frontend | HTML5 + CSS3 + JavaScript + Chart.js | Single-file panels, no build step |
| Storage | SQLite (3 separate databases) | Zero-config, isolated per module |
| Simulation | Python requests + asyncio | Reproducible attack scenarios |

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Training events | 100,000 |
| User personas in training | 6 |
| Auth attack types detected | 15 |
| Financial attack types detected | 2 |
| Total attacks covered | 17 |
| ML inference latency | < 10ms |
| Financial loss across all attacks | ₹0 |
| Honeypot endpoints | 5 |
| Hidden form fields | 3 |

---

## Team

Built for the AI & FinTech Security Track — National Level Hackathon.

---

*Three modules. Three threat domains. One platform. Zero financial loss.*

