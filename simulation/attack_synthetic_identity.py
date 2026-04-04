import time
import requests
import random
import threading
try:
    import simulation.base as base
except ImportError:
    import base

ATTACK_TYPE = "synthetic_identity"
BASE_URL = "http://localhost:5000"
ATTACK_TIMEOUT = 5

MULES = [
  {"name": "Aryan Kapoor", "pan": "ABCPK7823Q", "aadhaar": "4521"},
  {"name": "Zara Sheikh", "pan": "BCDSK8934R", "aadhaar": "3847"},
  {"name": "Dev Malhotra", "pan": "CDEDM9045S", "aadhaar": "7291"},
  {"name": "Isha Tiwari", "pan": "DEFIT0156T", "aadhaar": "6134"},
  {"name": "Rohan Saxena", "pan": "EFGRS1267U", "aadhaar": "9823"},
  {"name": "Prachi Bhatia", "pan": "FGHPB2378V", "aadhaar": "2456"},
  {"name": "Kabir Chandra", "pan": "GHIKC3489W", "aadhaar": "8012"},
  {"name": "Nisha Reddy", "pan": "HIJNR4590X", "aadhaar": "5673"},
  {"name": "Yash Thakur", "pan": "IJKYT5601Y", "aadhaar": "1298"},
  {"name": "Meghna Pillai", "pan": "JKLMP6712Z", "aadhaar": "4567"},
  {"name": "Arjun Shetty", "pan": "KLMAS7823A", "aadhaar": "7890"},
  {"name": "Tanvi Ghosh", "pan": "LMNTG8934B", "aadhaar": "3214"},
  {"name": "Vivek Nair", "pan": "MNOVM9045C", "aadhaar": "6543"},
  {"name": "Pooja Menon", "pan": "NOPPM0156D", "aadhaar": "9876"},
  {"name": "Rahul Dubey", "pan": "OPQRD1267E", "aadhaar": "2109"}
]

DEVICE = {
    "device_fingerprint": "d4f8a2c1b9e3f7d2a5c8b1e4f9d2a7c3",
    "screen_resolution": "1920x1080",
    "timezone": "Asia/Kolkata",
    "browser_ua": "Mozilla/5.0 Chrome/120.0 Safari/537.36"
}

def create_synthetic_account(mule, delay, mode):
    session = requests.Session()
    
    account_id = f"SYN-{random.randint(100000, 999999)}"
    form_duration = random.randint(800, 1400)
    
    payload = {
        "account_id": account_id,
        "name": mule["name"],
        "pan_number": mule["pan"],
        "aadhaar_last4": mule["aadhaar"],
        "form_fill_duration_ms": form_duration,
        **DEVICE
    }
    
    try:
        if mode == "manual":
            input(f"\nPress Enter to POST /api/identity/create-account ({mule['name']})...")
            
        res = session.post(f"{BASE_URL}/api/identity/create-account", json=payload, timeout=ATTACK_TIMEOUT)
        data = res.json()
        print(f"[SYNTH] Creating account | {mule['name']} | PAN: {mule['pan']} | Fill: {form_duration}ms | Status: {data.get('status')} | Risk: {data.get('risk_score')}")
        
    except requests.exceptions.RequestException as e:
        print(f"[!] Target unreachable: {e}")
        return None, False

    time.sleep(delay)
    
    # Check for global suspension
    if data.get('action') == "suspend_all":
         print(f"[DETECTED] Device fingerprint blacklisted. All synthetic accounts suspended.")
         return account_id, True

    # Step 2: Apply for credit
    try:
        if mode == "manual":
            input(f"Press Enter to POST /api/identity/apply-credit ({account_id})...")
            
        res2 = session.post(f"{BASE_URL}/api/identity/apply-credit", json={"account_id": account_id, "requested_amount": 50000}, timeout=ATTACK_TIMEOUT)
        data2 = res2.json()
        print(f"[CREDIT] Applying ₹50,000 credit | {mule['name']} | Status: {data2.get('status')} | Risk: {data2.get('risk_score')}")
        
    except requests.exceptions.RequestException as e:
        print(f"[!] Target unreachable: {e}")
        return None, False

    time.sleep(delay)
    return account_id, False

def run_attack(delay, mode="bot"):
    print(f"\n[***] Initializing Synthetic Identity Attack [***]\n")
    print(f"Loaded {len(MULES)} synthetic profiles.")
    
    for i, mule in enumerate(MULES):
        if base.should_stop(ATTACK_TYPE):
            print("\n[!] Attack manually stopped by user.")
            break
            
        account_id, is_suspended = create_synthetic_account(mule, delay, mode)
        if is_suspended:
            blocked_credit = (15 - i) * 50000
            print(f"\n[!!!] FATAL OVERRIDE: Attack halted by AetherSense AI.")
            print(f"Total Future Credit Protected: ₹{blocked_credit:,}")
            break

def run(delay=0.8, mode="bot"):
    thread = threading.Thread(target=run_attack, args=(delay, mode))
    thread.daemon = True
    thread.start()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Synthetic Identity DB Demo')
    parser.add_argument('--delay', type=float, default=0.8, help='Delay between requests in seconds')
    parser.add_argument('--mode', type=str, choices=['bot', 'manual'], default='bot', help='Execution mode')
    args = parser.parse_args()
    
    # Override for direct terminal testing to block daemon mode exit
    run_attack(args.delay, args.mode)
