from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import json
import time
from threading import Thread
from web3 import Web3
from dotenv import load_dotenv

# ✅ Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# ✅ Environment variables
INFURA_URL = os.getenv("INFURA_URL", "https://sepolia.infura.io/v3/57ea67cde27f45f9af5a69bdc5c92332")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x59B649856d8c5Fb6991d30a345f0b923eA91a3f7")

# ✅ Web3 setup
web3 = Web3(Web3.HTTPProvider(INFURA_URL))

# ✅ Load smart contract ABI
with open("contract_abi.json") as f:
    contract_abi = json.load(f)

contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)

# ✅ Define base directory for JSON panel records
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PANELS_DIR = os.path.join(BASE_DIR, "panels")

# ✅ Route 1: Root check
@app.route('/')
def home():
    return "✅ Oracle Backend is running and listening for blockchain events!"

# ✅ Route 2: Serve filtered DPP JSON
@app.route("/api/dpp/<panel_id>", methods=["GET"])
def get_filtered_dpp(panel_id):
    access_level = request.args.get("access", "public").lower()
    file_path = os.path.join(PANELS_DIR, f"{panel_id}.json")

    if not os.path.exists(file_path):
        return jsonify({"error": "Panel record not found."}), 404

    with open(file_path, "r") as f:
        dpp_data = json.load(f)

    allowed_roles = ["Public"]
    if access_level == "tier1":
        allowed_roles += ["Tier 1"]
    elif access_level == "tier2":
        allowed_roles += ["Tier 1", "Tier 2"]

    filtered = {k: v for k, v in dpp_data.items() if v.get("Access_Tier") in allowed_roles}
    return jsonify(filtered)

# ✅ Route 3: Return SHA3 hash
@app.route("/api/hash/<panel_id>", methods=["GET"])
def get_panel_hash(panel_id):
    file_path = os.path.join(PANELS_DIR, f"{panel_id}.json")
    if not os.path.exists(file_path):
        return jsonify({"error": "Panel not found"}), 404

    with open(file_path, "rb") as f:
        file_bytes = f.read()
        hash_hex = web3.keccak(file_bytes).hex()
    return jsonify({"panel_id": panel_id, "sha3_hash": hash_hex})

# ✅ Route 4: Serve full JSON file directly
@app.route("/panels/<path:filename>")
def serve_panel_file(filename):
    return send_from_directory(PANELS_DIR, filename)

# ✅ Function to update panel JSON when an event is emitted
def update_panel_json(panel_id, event_type, fault_type, fault_severity, action_taken, event_hash):
    path = os.path.join(PANELS_DIR, f"{panel_id}.json")
    if not os.path.exists(path):
        print(f"⚠️ JSON not found for {panel_id}")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    update_block = {
        "fault_id": event_hash,
        "fault_type": fault_type,
        "fault_severity_level": fault_severity,
        "action_taken": action_taken,
        "resolved": False,
        "resolution_timestamp": timestamp
    }

    if event_type == "installation":
        data["fault_log_installation"].update(update_block)
    else:
        data["fault_log_operation"].update(update_block)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Updated {panel_id}.json after {event_type} event")

# ✅ Event listener thread
def listen_for_events():
    print("👂 Listening for PanelEventAdded events in real-time...")
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

                print(f"🔹 New event → {panel_id} | {event_type} | {fault_type}")
                update_panel_json(panel_id, event_type, fault_type, fault_severity, action_taken, event_hash)

        except Exception as e:
            print("⚠️ Error in event listener:", e)
        time.sleep(10)

# ✅ Start event listener in background
Thread(target=listen_for_events, daemon=True).start()

# ✅ Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
