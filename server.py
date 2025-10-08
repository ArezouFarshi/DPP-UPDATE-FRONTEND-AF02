from flask import Flask, jsonify, request
import os
import json
from eth_account import Account
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
@app.route('/')
def home():
    return "✅ Oracle Backend is running and healthy!"


INFURA_URL = os.getenv("INFURA_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
ORACLE_WALLET = os.getenv("ORACLE_WALLET")

with open("contract_abi.json") as f:
    contract_abi = json.load(f)

web3 = Web3(Web3.HTTPProvider(INFURA_URL))
account = Account.from_key(PRIVATE_KEY)
contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)

@app.route("/api/dpp/<panel_id>", methods=["GET"])
def get_filtered_dpp(panel_id):
    access_level = request.args.get("access", "public").lower()
    file_path = os.path.join("pnels", f"{panel_id}.json")

    if not os.path.exists(file_path):
        return jsonify({"error": "Panel record not found."}), 404

    with open(file_path, "r") as file:
        dpp_data = json.load(file)

    filtered = filter_dpp_for_user(dpp_data, access_level)
    return jsonify(filtered)

def filter_dpp_for_user(dpp_json, user_role):
    allowed_roles = ["public"]
    if user_role == "tier1":
        allowed_roles.append("Tier 1")
    elif user_role == "tier2":
        allowed_roles.extend(["Tier 1", "Tier 2"])

    filtered = {}
    for key, section in dpp_json.items():
        if isinstance(section, dict) and section.get("Access_Tier", "Public") in allowed_roles:
            filtered[key] = section
    return filtered

@app.route("/api/hash/<panel_id>", methods=["GET"])
def get_panel_hash(panel_id):
    file_path = os.path.join("pnels", f"{panel_id}.json")

    if not os.path.exists(file_path):
        return jsonify({"error": "Panel record not found."}), 404

    with open(file_path, "rb") as file:
        file_bytes = file.read()
        hash_hex = web3.keccak(file_bytes).hex()
    return jsonify({"panel_id": panel_id, "sha3_hash": hash_hex})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
