from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from web3 import Web3
from threading import Thread
import os
import json
import time
from dotenv import load_dotenv
from oracle_automation import process_and_anchor  # Import helper

# ✅ Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# ✅ Environment variables
INFURA_URL = os.getenv("INFURA_URL", "https://sepolia.infura.io/v3/57ea67cde27f45f9af5a69bdc5c92332")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x59B649856d8c5Fb6991d30a345f0b923eA91a3f7")

# ✅ Web3 setup
web3 = Web3(Web3.HTTPProvider(INFURA_URL))

# ✅ Load ABI
with open("contract_abi.json") as f:
    contract_abi = json.load(f)

contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)

# ✅ JSON panels directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PANELS_DIR = os.path.join(BASE_DIR, "panels")

# -------------------- ROUTES --------------------

@app.route("/")
def home():
    return "✅ Oracle Backend is running and watching blockchain events!"

@app.route("/api/dpp/<panel_id>", methods=["GET"])
def get_filtered_dpp(panel_id):
    access_level = request.args.get("access", "public").lower()
    file_path = os.path.join(PANELS_DIR, f"{panel_id}.json")

    if not os.path.exists(file_path):
        return jsonify({"error": "Panel not found"}), 404

    with open(file_path, "r") as f:
        data = json.load(f)

    allowed_roles = ["Public"]
    if access_level == "tier1":
        allowed_roles += ["Tier 1"]
    elif access_level == "tier2":
        allowed_roles += ["Tier 1", "Tier 2"]

    filtered = {k: v for k, v in data.items() if v.get("Access_Tier") in allowed_roles}
    return jsonify(filtered)

@app.route("/api/hash/<panel_id>")
def get_hash(panel_id):
    file_path = os.path.join(PANELS_DIR, f"{panel_id}.json")
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    with open(file_path, "rb") as f:
        h = web3.keccak(f.read()).hex()
    return jsonify({"panel_id": panel_id, "sha3_hash": h})

@app.route("/panels/<path:filename>")
def serve_panel(filename):
    return send_from_directory(PANELS_DIR, filename)

# -------------------- EVENT LISTENER --------------------

def listen_for_events():
    print("👂 Listening for PanelEventAdded events in real time...")
    event_filter = contract.events.PanelEventAdded.create_filter(fromBlock="latest")

    while True:
        try:
            for event in event_filter.get_new_entries():
                args = event["args"]
                panel_id = args["panelId"]
                event_type = args["eventType"]
                fault_type = args["faultType"]
                fault_severity = args["faultSeverity"]
                action_taken = args["actionTaken"]
                event_hash = args["eventHash"].hex()

                print(f"🔹 New Event → {panel_id} | {event_type} | {fault_type}")

                # Call update helper
                process_and_anchor(
                    panel_id=panel_id,
                    event_type=event_type,
                    fault_type=fault_type,
                    fault_severity=fault_severity,
                    action_taken=action_taken,
                    event_hash=event_hash
                )

        except Exception as e:
            print("⚠️ Error in event listener:", e)

        time.sleep(10)

# ✅ Start background thread
Thread(target=listen_for_events, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
