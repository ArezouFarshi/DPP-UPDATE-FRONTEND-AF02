# worker.py
import os
import json
import time
from web3 import Web3
from web3.middleware import geth_poa_middleware
from dotenv import load_dotenv
from oracle_automation import process_and_anchor

# ---------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------
load_dotenv()

# You already confirmed these values:
INFURA_WS = "wss://sepolia.infura.io/ws/v3/57ea67cde27f45f9af5a69bdc5c92332"
CONTRACT_ADDRESS = "0x59B649856d8c5Fb6991d30a345f0b923eA91a3f7"

# ---------------------------------------------------------
# Web3 setup with WebSocket provider
# ---------------------------------------------------------
web3 = Web3(Web3.WebsocketProvider(INFURA_WS, websocket_timeout=30))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

# ---------------------------------------------------------
# Load ABI (ensure file is named contract_abi.json in repo root)
# ---------------------------------------------------------
with open("contract_abi.json", "r", encoding="utf-8") as f:
    contract_abi = json.load(f)

contract = web3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=contract_abi
)

# ---------------------------------------------------------
# Event listener loop
# ---------------------------------------------------------
def listen_for_events():
    print("👂 Worker listening for PanelEventAdded events in real time...")
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
                event_hash = args["eventHash"].hex()  # bytes32 → hex string

                print(f"🔹 New Event → {panel_id} | {event_type} | {fault_type} | {fault_severity} | {action_taken}")

                # Update JSON + anchor on-chain
                process_and_anchor(
                    panel_id=panel_id,
                    event_type=event_type,
                    fault_type=fault_type,
                    fault_severity=fault_severity,
                    action_taken=action_taken,
                    event_hash=event_hash
                )

        except Exception as e:
            print(f"⚠️ Worker error: {type(e).__name__}: {e}")
            time.sleep(5)

        time.sleep(2)

# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------
if __name__ == "__main__":
    listen_for_events()
