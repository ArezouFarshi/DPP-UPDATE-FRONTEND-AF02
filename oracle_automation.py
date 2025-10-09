import json
import os
import datetime
from web3 import Web3

# ✅ Setup
INFURA_URL = "https://sepolia.infura.io/v3/57ea67cde27f45f9af5a69bdc5c92332"
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

# Oracle wallet (TEST ONLY)
ORACLE_PRIVATE_KEY = "0fc530d3f88969a28bf0b9e935aee66e6c1294a2329c12826500cfb673a39f79"
ORACLE_ADDRESS = w3.eth.account.from_key(ORACLE_PRIVATE_KEY).address

# Smart contract setup
CONTRACT_ADDRESS = Web3.to_checksum_address("0x59B649856d8c5Fb6991d30a345f0b923eA91a3f7")
CONTRACT_ABI = json.load(open("contract_abi.json"))
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

# Directory for JSON
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PANELS_DIR = os.path.join(BASE_DIR, "panels")

def process_and_anchor(panel_id, event_type, fault_type, fault_severity, action_taken, event_hash):
    """Update JSON file when a blockchain event is detected."""
    path = os.path.join(PANELS_DIR, f"{panel_id}.json")
    if not os.path.exists(path):
        print(f"⚠️ Panel record not found: {panel_id}")
        return

    with open(path, "r", encoding="utf-8") as f:
        panel_json = json.load(f)

    timestamp = datetime.datetime.utcnow().isoformat()

    fault_data = {
        "fault_id": event_hash,
        "fault_type": fault_type,
        "fault_severity_level": fault_severity,
        "action_taken": action_taken,
        "resolved": False,
        "resolution_timestamp": timestamp
    }

    # Choose section
    if event_type == "installation":
        section = "fault_log_installation"
    else:
        section = "fault_log_operation"

    for key, val in fault_data.items():
        panel_json[section][key] = val

    # Save
    with open(path, "w", encoding="utf-8") as f:
        json.dump(panel_json, f, indent=2)

    print(f"✅ JSON updated for {panel_id} ({event_type})")

    # Optional blockchain anchoring
    try:
        section_bytes = json.dumps(panel_json[section], sort_keys=True).encode("utf-8")
        section_hash = Web3.keccak(section_bytes).hex()
        nonce = w3.eth.get_transaction_count(ORACLE_ADDRESS)

        tx = contract.functions.addPanelEvent(
            panel_id,
            event_type,
            fault_type,
            fault_severity,
            action_taken,
            Web3.to_bytes(hexstr=section_hash)
        ).build_transaction({
            "from": ORACLE_ADDRESS,
            "nonce": nonce,
            "gas": 300000,
            "gasPrice": w3.to_wei("20", "gwei")
        })

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=ORACLE_PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"🔗 Anchored update on-chain → {tx_hash.hex()}")

    except Exception as e:
        print("⚠️ Skipped on-chain update:", e)
