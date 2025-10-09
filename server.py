from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import json
import time
import threading
from eth_account import Account
from web3 import Web3
from dotenv import load_dotenv
from oracle_automation import process_and_anchor   # ✅ Import your updater function

# =====================================================
# 1️⃣ Load environment and initialize Flask
# =====================================================
load_dotenv()
app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "✅ Oracle Backend is running and listening for events!"

# =====================================================
# 2️⃣ Web3 and Smart Contract Setup
# =====================================================
INFURA_URL = os.getenv("INFURA_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
ORACLE_WALLET = os.getenv("ORACLE_WALLET")

web3 = Web3(Web3.HTTPProvider(INFURA_URL))
account = Account.from_key(PRIVATE_KEY)

with open("contract_abi.json") as f:
    contract_abi = json.load(f)

contract = web3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=contract_abi
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# =====================================================
# 3️⃣ API ROUTES
# =====================================================

# 🔹 Route 1: Return filtered DPP data by access tier
@app.route("/api/dpp/<panel_id>", methods=["GET"])
def get_filtered_dpp(panel_id):
    access_level = request.args.get("access", "public").lower()
    file_path = os.path.join(BASE_DIR, "panels", f"{panel_id}.json")

    if not os.path.exists(file_path):
        return jsonify({"error": f"Panel {panel_id} not found"}), 404

    with open(file_path, "r") as f:
        dpp_data = json.load(f)

    filtered = filter_dpp_for_user(dpp_data, access_level)
    return jsonify(filtered)

def filter_dpp_for_user(dpp_json, user_role):
    allowed_roles = ["Public"]
    if user_role == "tier1":
        allowed_roles.extend(["Tier 1"])
    elif user_role == "tier2":
        allowed_roles.extend(["Tier 1", "Tier 2"])

    filtered = {}
    for key, section in dpp_json.items():
        if isinstance(section, dict) and section.get("Access_Tier") in allowed_roles:
            filtered[key] = section
    return filtered


# 🔹 Route 2: Return SHA3 hash of a specific panel JSON
@app.route("/api/hash/<panel_id>", methods=["GET"])
def get_panel_hash(panel_id):
    file_path = os.path.join(BASE_DIR, "panels", f"{panel_id}.json")

    if not os.path.exists(file_path):
        return jsonify({"error": f"Panel {panel_id} not found"}), 404

    with open(file_path, "rb") as f:
        file_bytes = f.read()
        hash_hex = web3.keccak(file_bytes).hex()

    return jsonify({"panel_id": panel_id, "sha3_hash": hash_hex})


# 🔹 Route 3: Serve JSON files directly (frontend access)
@app.route("/panels/<path:filename>")
def serve_panel_file(filename):
    return send_from_directory(os.path.join(BASE_DIR, "panels"), filename)


# =====================================================
# 4️⃣ BACKGROUND EVENT LISTENER
# =====================================================
def watch_contract_events():
    print("👀 Watching for blockchain events in real-time...")
    latest_block = web3.eth.block_number

    while True:
        try:
            # ✅ Adjust to your Solidity event name
            events = contract.events.PanelEventAdded.get_logs(fromBlock=latest_block + 1)
            for evt in events:
                args = evt["args"]
                print("🔹 New blockchain event detected:", args)

                panel_id = args.get("panelId")
                event_type = args.get("eventType")
                fault_type = args.get("faultType", None)
                fault_severity = args.get("faultSeverity", None)
                action_taken = args.get("actionTaken", None)
                event_hash = args.get("eventHash")

                # ✅ Prepare payload
                payload = {
                    "panel_id": panel_id,
                    "fault_data": {
                        "fault_id": fault_type,
                        "fault_type": fault_type,
                        "fault_severity_level": fault_severity,
                        "action_taken": action_taken,
                        "event_hash": event_hash
                    }
                }

                # ✅ Automatically update and re-anchor JSON file
                process_and_anchor(payload, event_type)

            latest_block = web3.eth.block_number

        except Exception as e:
            print("⚠️ Event listener error:", e)

        time.sleep(10)  # Poll every 10 seconds


# =====================================================
# 5️⃣ STARTUP
# =====================================================
threading.Thread(target=watch_contract_events, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
