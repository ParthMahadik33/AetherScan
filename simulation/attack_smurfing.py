import time
import random
import argparse
import sys
import requests
import datetime
from colorama import init, Fore, Style

init(autoreset=True)

try:
    import simulation.base as base
except ImportError:
    import base

ATTACK_TYPE = "smurfing"

MULES = [
    {"id": "PV-119023", "name": "Priya Sharma"},
    {"id": "PV-220341", "name": "Amit Verma"},
    {"id": "PV-330812", "name": "Sneha Patel"},
    {"id": "PV-441293", "name": "Rohit Gupta"},
    {"id": "PV-552074", "name": "Anjali Desai"},
    {"id": "PV-663855", "name": "Ravi Kumar"},
    {"id": "PV-774636", "name": "Deepak Nair"},
    {"id": "PV-885417", "name": "Pooja Iyer"},
    {"id": "PV-996198", "name": "Karan Malhotra"},
    {"id": "PV-107979", "name": "Neha Singh"},
    {"id": "PV-218760", "name": "Vikram Joshi"},
    {"id": "PV-329541", "name": "Simran Kaur"},
    {"id": "PV-430322", "name": "Arjun Reddy"},
    {"id": "PV-541103", "name": "Meera Pillai"},
    {"id": "PV-651884", "name": "Suresh Nambiar"},
    {"id": "PV-762665", "name": "Divya Menon"},
    {"id": "PV-873446", "name": "Rahul Sinha"},
    {"id": "PV-984227", "name": "Kavya Rao"},
    {"id": "PV-095008", "name": "Aditya Bose"},
    {"id": "PV-106789", "name": "Tanvi Shah"}
]

SOURCE_ACCOUNT = "PV-004821"
API_URL = "http://localhost:5000/api/transaction"

def execute_attack(delay=1.5, mode="bot"):
    print(Fore.CYAN + f"\n[***] Initializing Smurfing Attack from {SOURCE_ACCOUNT} [***]\n")
    
    total_transactions = 20
    mule_idx = 0
    
    for n in range(1, total_transactions + 1):
        if base.should_stop("smurfing"):
            print(Fore.RED + "[STOP] Attack stopped by controller.")
            break
            
        mule = MULES[mule_idx]
        amount = random.randint(9200, 9900)
        
        payload = {
            "account_id": SOURCE_ACCOUNT,
            "recipient_id": mule["id"],
            "recipient_name": mule["name"],
            "amount": amount,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
        try:
            resp = requests.post(API_URL, json=payload, timeout=5)
            data = resp.json()
            status = data.get("status", "UNKNOWN")
            risk = data.get("risk_score", 0)
            action = data.get("action", "")
            
            # Print format
            status_color = Fore.GREEN if status in ["COMPLETED", "NORMAL"] else (
                Fore.YELLOW if status in ["HELD", "MONITORING"] else (
                    Fore.MAGENTA if status == "ALERT" else Fore.RED
                )
            )
            
            print(f"[SMURF] Txn #{n} | ₹{amount} -> {mule['name']} | Status: {status_color}{status}{Style.RESET_ALL} | Risk: {risk}")
            
            if action == "reverse_all":
                print(Fore.RED + "DETECTED - Account frozen. Attack failed." + Style.RESET_ALL)
                break
                
        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"[!] Connection error: {e}")
            break
            
        mule_idx = (mule_idx + 1) % len(MULES)
        
        if mode == "bot" and n < total_transactions:
            # Sleep in tiny increments to allow quick stop
            sleep_steps = int(delay * 10)
            for _ in range(sleep_steps):
                if base.should_stop("smurfing"):
                    break
                time.sleep(0.1)
        elif mode == "manual" and n < total_transactions:
            input("Press Enter to send next transaction...")

def run(delay=1.5, mode="bot"):
    execute_attack(delay, mode)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Smurfing Attack Simulation")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay between transactions (seconds)")
    parser.add_argument("--mode", default="bot", choices=["bot", "manual"], help="Execution mode")
    args = parser.parse_args()
    
    run(delay=args.delay, mode=args.mode)
