import json
import os
import datetime
from web3 import Web3

# Connect to Infura
INFURA_URL = "https://sepolia.infura.io/v3/57ea67cde27f45f9af5a69bdc5c92332"
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

# Wallet details (test only!)
ORACLE_PRIVATE_KEY = "0fc530d3f88969a28bf0b9e935aee66e6c1294a2329c12826500cfb673a39f79"
ORACLE_ADDRESS = w3.eth.account.from_key(ORACLE_PRIVATE_KEY).address

# Smart contract setup
CONTRACT_ADDRESS = Web3.to_checksum_address("0xb8935eBEb1dA663C187fc9090b77E1972A909e12")
CONTRACT_ABI = json.load(open("contract_abi.json"))  # Make sure ABI file is present
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

def process_and_anchor(payload, event_type):
    panel_id = payload.get("panel_id")
    fault_data = payload.get("fault_data")  # Dictionary with keys like fault_id, fault_type, etc.

    if not panel_id or not fault_data:
        raise ValueError("Missing panel_id or fault_data")

    # --- Step 1: Load JSON file ---
    panel_path = f"panels/{panel_id}.json"
    if not os.path.exists(panel_path):
        raise FileNotFoundError(f"Panel record not found: {panel_id}")

    with open(panel_path, "r", encoding="utf-8") as f:
        panel_json = json.load(f)

    # --- Step 2: Update the appropriate section ---
    timestamp = datetime.datetime.utcnow().isoformat()
    fault_data["resolution_timestamp"] = timestamp

    if event_type == "installation":
        section = "fault_log_installation"
    elif event_type == "operation":
        section = "fault_log_operation"
    else:
        raise ValueError("Invalid event_type: must be 'installation' or 'operation'")

    for key, value in fault_data.items():
        panel_json[section][key] = value

    # --- Step 3: Save JSON ---
    with open(panel_path, "w", encoding="utf-8") as f:
        json.dump(panel_json, f, indent=2)

    # --- Step 4: Hash the section ---
    section_bytes = json.dumps(panel_json[section], sort_keys=True).encode("utf-8")
    section_hash = Web3.keccak(section_bytes).hex()

    # --- Step 5: Send to smart contract ---
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

    return panel_id, event_type, tx_hash.hex()
