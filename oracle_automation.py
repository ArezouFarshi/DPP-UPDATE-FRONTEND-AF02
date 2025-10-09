import json
import os
import datetime
import time
from web3 import Web3

# ✅ Step 1: Connect to Infura
INFURA_URL = "https://sepolia.infura.io/v3/57ea67cde27f45f9af5a69bdc5c92332"
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

# ✅ Step 2: Oracle Wallet (TEST ONLY)
ORACLE_PRIVATE_KEY = "0fc530d3f88969a28bf0b9e935aee66e6c1294a2329c12826500cfb673a39f79"
ORACLE_ADDRESS = w3.eth.account.from_key(ORACLE_PRIVATE_KEY).address

# ✅ Step 3: Smart Contract setup
CONTRACT_ADDRESS = Web3.to_checksum_address("0x59B649856d8c5Fb6991d30a345f0b923eA91a3f7")
CONTRACT_ABI = json.load(open("contract_abi.json"))
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

# ✅ Step 4: Absolute path for panel JSON folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PANELS_DIR = os.path.join(BASE_DIR, "panels")


# =====================================================
# FUNCTION: process_and_anchor
# =====================================================
def process_and_anchor(payload, event_type):
    """
    Updates the panel's JSON record with fault or event data,
    recalculates its hash, and anchors it to the blockchain.
    """
    panel_id = payload.get("panel_id")
    fault_data = payload.get("fault_data")

    if not panel_id or not fault_data:
        raise ValueError("Missing panel_id or fault_data")

    panel_path = os.path.join(PANELS_DIR, f"{panel_id}.json")
    if not os.path.exists(panel_path):
        raise FileNotFoundError(f"Panel record not found: {panel_id}")

    with open(panel_path, "r", encoding="utf-8") as f:
        panel_json = json.load(f)

    # --- Step 2: Update section ---
    timestamp = datetime.datetime.utcnow().isoformat()
    fault_data["resolution_timestamp"] = timestamp

    if event_type.lower() == "installation":
        section = "fault_log_installation"
    elif event_type.lower() == "operation":
        section = "fault_log_operation"
    else:
        raise ValueError("Invalid event_type: must be 'installation' or 'operation'")

    for key, value in fault_data.items():
        panel_json[section][key] = value

    # --- Step 3: Save updated JSON ---
    with open(panel_path, "w", encoding="utf-8") as f:
        json.dump(panel_json, f, indent=2)

    # --- Step 4: Compute hash and anchor ---
    section_bytes = json.dumps(panel_json[section], sort_keys=True).encode("utf-8")
    section_hash = Web3.keccak(section_bytes).hex()

    nonce = w3.eth.get_transaction_count(ORACLE_ADDRESS)
    tx = contract.functions.recordFault(
        panel_id,
        event_type,
        section_hash
    ).build_transaction({
        'from': ORACLE_ADDRESS,
        'nonce': nonce,
        'gas': 300000,
        'gasPrice': w3.to_wei('20', 'gwei')
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=ORACLE_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    print(f"✅ Anchored {panel_id} ({event_type}) → {tx_hash.hex()}")
    return panel_id, event_type, tx_hash.hex()


# =====================================================
# OPTIONAL: LISTENER (for standalone runs)
# =====================================================
def handle_event(event):
    args = event["args"]
    payload = {
        "panel_id": args["panelId"],
        "fault_data": {
            "fault_id": args["faultType"],
            "fault_type": args["faultType"],
            "fault_severity_level": args["faultSeverity"],
            "action_taken": args["actionTaken"],
            "event_hash": args["eventHash"]
        }
    }
    process_and_anchor(payload, args["eventType"])


def watch_events():
    print("👂 Listening for PanelEventAdded events...")
    event_filter = contract.events.PanelEventAdded.create_filter(fromBlock="latest")

    while True:
        try:
            for event in event_filter.get_new_entries():
                print("🔹 New event detected:", event["args"])
                handle_event(event)
        except Exception as e:
            print("⚠️ Event listener error:", e)
        time.sleep(10)


# Run listener manually if script executed directly
if __name__ == "__main__":
    watch_events()
