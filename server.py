from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from web3 import Web3
import os, json
from dotenv import load_dotenv
from oracle_automation import process_and_anchor

load_dotenv()

INFURA_WS = "wss://sepolia.infura.io/ws/v3/57ea67cde27f45f9af5a69bdc5c92332"
CONTRACT_ADDRESS = Web3.to_checksum_address("0x59B649856d8c5Fb6991d30a345f0b923eA91a3f7")

app = Flask(__name__)
CORS(app)

# ✅ FIX: use LegacyWebSocketProvider
web3 = Web3(Web3.LegacyWebSocketProvider(INFURA_WS, websocket_timeout=30))

with open("contract_abi.json", "r", encoding="utf-8") as f:
    contract_abi = json.load(f)

contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PANELS_DIR = os.path.join(BASE_DIR, "panels")

@app.route("/")
def home():
    return "✅ Oracle Backend is running and serving API routes!"

@app.route("/health")
def health():
    try:
        return {"ok": True, "latest_block": web3.eth.block_number}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.route("/api/dpp/<panel_id>", methods=["GET"])
def get_filtered_dpp(panel_id):
    access_level = request.args.get("access", "public").lower()
    file_path = os.path.join(PANELS_DIR, f"{panel_id}.json")
    if not os.path.exists(file_path):
        return jsonify({"error": "Panel not found"}), 404
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    allowed_roles = ["Public"]
    if access_level == "tier1":
        allowed_roles += ["Tier 1"]
    elif access_level == "tier2":
        allowed_roles += ["Tier 1", "Tier 2"]
    filtered = {k: v for k, v in data.items() if isinstance(v, dict) and v.get("Access_Tier") in allowed_roles}
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
