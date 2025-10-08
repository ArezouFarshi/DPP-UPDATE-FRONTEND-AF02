from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import json
from eth_account import Account
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# ✅ Root route to verify backend health
@app.route('/')
def home():
    return "✅ Oracle Backend is running!"

# Environment variables
INFURA_URL = os.getenv("INFURA_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
ORACLE_WALLET = os.getenv("ORACLE_WALLET")

# Load smart contract ABI
with open("contract_abi.json") as f:
    contract_abi = json.load(f)

# Web3 setup
web3 = Web3(Web3.HTTPProvider(INFURA_URL))
account = Account.from_key(PRIVATE_KEY)
contract = web3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=contract_abi
)

# ✅ Use absolute path so Render always finds your JSON files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ✅ Route 1: Serve DPP JSON filtered by access tier
@app.route("/api/dpp/<panel_id>", methods=["GET"])
def get_filtered_dpp(panel_id):
    access_level = request.args.get("access", "public").lower()
    file_path = os.path.join(BASE_DIR, "panels", f"{panel_id}.json")  # ✅ fixed folder name

    if not os.path.exists(file_path):
        return jsonify({"error": "Panel record not found."}), 404

    with open(file_path, "r") as file:
        dpp_data = json.load(file)

    filtered = filter_dpp_for_user(dpp_data, access_level)
    return jsonify(filtered)


def filter_dpp_for_user(dpp_json, user_role):
    allowed_roles = ["Public"]

    if user_role == "tier1":
        allowed_roles.extend(["Public", "Tier 1"])
    elif user_role == "tier2":
        allowed_roles.extend(["Public", "Tier 1", "Tier 2"])

    filtered = {}
    for key, section in dpp_json.items():
        if isinstance(section, dict) and section.get("Access_Tier") in allowed_roles:
            filtered[key] = section
    return filtered

# ✅ Route 2: Return SHA3 hash for a given panel JSON
@app.route("/api/hash/<panel_id>", methods=["GET"])
def get_panel_hash(panel_id):
    file_path = os.path.join(BASE_DIR, "panels", f"{panel_id}.json")  # ✅ fixed folder name

    if not os.path.exists(file_path):
        return jsonify({"error": "Panel record not found."}), 404

    with open(file_path, "rb") as file:
        file_bytes = file.read()
        hash_hex = web3.keccak(file_bytes).hex()

    return jsonify({"panel_id": panel_id, "sha3_hash": hash_hex})

# ✅ Route 3: Directly serve JSON files (for frontend "Load DPP JSON" button)
@app.route("/panels/<path:filename>")
def serve_panel_file(filename):
    return send_from_directory(os.path.join(BASE_DIR, "panels"), filename)
# --- EVENT LISTENER THREAD ---
from threading import Thread
import time

def watch_contract_events():
    print("👀 Watching for blockchain events...")
    latest_block = web3.eth.block_number

    while True:
        try:
            # Listen for recordFault events
            events = contract.events.recordFault.get_logs(fromBlock=latest_block)
            for evt in events:
                args = evt["args"]
                print("🔹 New event detected:", args)

                panel_id = args.get("panelId")
                event_type = args.get("eventType")
                section_hash = args.get("sectionHash")

                # Optional: call process_and_anchor to update JSON automatically
                from oracle_automation import process_and_anchor
                payload = {"panel_id": panel_id, "fault_data": {"section_hash": section_hash}}
                process_and_anchor(payload, event_type)

            latest_block = web3.eth.block_number
        except Exception as e:
            print("⚠️ Event listener error:", e)

        time.sleep(10)  # Check every 10 seconds

# Start background thread
Thread(target=watch_contract_events, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
