import os
import json
import time
from typing import Dict, Any, List
from flask import Flask, jsonify, request
from web3 import Web3
from eth_account import Account

# -------------------------------------------------------------------
# Configuration (all sensitive values from environment variables)
# -------------------------------------------------------------------
INFURA_URL = os.getenv("INFURA_URL")              # Infura RPC endpoint
CONTRACT_ADDRESS = Web3.to_checksum_address(os.getenv("CONTRACT_ADDRESS"))
ABI_PATH = os.getenv("ABI_PATH", "contract_abi.json")
PANELS_DIR = os.getenv("PANELS_DIR", "panels")
CHAIN_ID = int(os.getenv("CHAIN_ID", "11155111")) # Sepolia default

PRIVATE_KEY = os.getenv("PRIVATE_KEY")            # Oracle private key
ORACLE_ADDRESS = os.getenv("ORACLE_ADDRESS")      # Oracle public address
ADMIN_ADDRESS = os.getenv("ADMIN_ADDRESS")        # Contract owner address

# -------------------------------------------------------------------
# Web3 setup
# -------------------------------------------------------------------
w3 = Web3(Web3.HTTPProvider(INFURA_URL))
if not w3.is_connected():
    raise RuntimeError("❌ Web3 not connected to RPC")

with open(ABI_PATH, "r", encoding="utf-8") as f:
    CONTRACT_ABI = json.load(f)

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

# Account object from private key (used if signing transactions)
account = Account.from_key(PRIVATE_KEY)
print(f"🔑 Oracle account loaded: {account.address}")

# -------------------------------------------------------------------
# Flask app
# -------------------------------------------------------------------
app = Flask(__name__)

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def load_panel_json(panel_id: str) -> Dict[str, Any]:
    path = os.path.join(PANELS_DIR, f"{panel_id}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Panel JSON not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def filter_by_access(dpp: Dict[str, Any], access: str) -> Dict[str, Any]:
    access = access.lower()
    allowed = {
        "public": {"Public"},
        "tier1": {"Public", "Tier 1"},
        "tier2": {"Public", "Tier 1", "Tier 2"}
    }
    tiers = allowed.get(access, {"Public"})
    filtered = {}
    for key, value in dpp.items():
        if isinstance(value, dict) and "Access_Tier" in value:
            if value.get("Access_Tier") in tiers:
                filtered[key] = value
        elif key in ("fault_log_installation", "fault_log_operation"):
            if "Tier 2" in tiers:
                filtered[key] = value
    return filtered

def fetch_events_for_panel(panel_id: str) -> List[Dict[str, Any]]:
    count = contract.functions.getEventCount(panel_id).call()
    events = []
    for idx in range(count):
        ok, color, status, prediction, reason, timestamp = contract.functions.getEventAt(panel_id, idx).call()
        events.append({
            "timestamp": int(timestamp),
            "color": color,
            "status": status,
            "prediction": int(prediction),
            "reason": reason,
            "ok": bool(ok)
        })
    return events

def merge_events_into_dpp(dpp: Dict[str, Any], events: List[Dict[str, Any]]) -> Dict[str, Any]:
    if "fault_log_installation" not in dpp:
        dpp["fault_log_installation"] = []
    if "fault_log_operation" not in dpp:
        dpp["fault_log_operation"] = []
    if "digital_twin_status" in dpp and events:
        latest = events[-1]
        dpp["digital_twin_status"]["current_visual_status"] = latest["status"]
        dpp["digital_twin_status"]["last_color_change"] = latest["color"]
    for evt in events:
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(evt["timestamp"])),
            "color": evt["color"],
            "status": evt["status"],
            "prediction": evt["prediction"],
            "reason": evt["reason"]
        }
        if evt["prediction"] in (1, 2, -1):
            dpp["fault_log_operation"].append(entry)
    return dpp

# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.get("/api/dpp/<panel_id>")
def get_dpp(panel_id: str):
    access = request.args.get("access", "public").lower()
    try:
        dpp = load_panel_json(panel_id)
    except FileNotFoundError:
        return jsonify({"error": "Panel JSON not found"}), 404
    try:
        events = fetch_events_for_panel(panel_id)
        dpp = merge_events_into_dpp(dpp, events)
    except Exception as e:
        dpp.setdefault("_warnings", []).append(f"Blockchain events not merged: {str(e)}")
    filtered = filter_by_access(dpp, access)
    return jsonify({"panel_id": panel_id, "access": access, "data": filtered})

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
