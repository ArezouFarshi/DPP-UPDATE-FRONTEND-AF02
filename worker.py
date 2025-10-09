import os, json, time
from web3 import Web3
from dotenv import load_dotenv
from oracle_automation import process_and_anchor

load_dotenv()

INFURA_WS = "wss://sepolia.infura.io/ws/v3/57ea67cde27f45f9af5a69bdc5c92332"
CONTRACT_ADDRESS = "0x59B649856d8c5Fb6991d30a345f0b923eA91a3f7"

# ✅ FIX: use WebSocketProvider (capital S)
web3 = Web3(Web3.WebSocketProvider(INFURA_WS, websocket_timeout=30))

with open("contract_abi.json", "r", encoding="utf-8") as f:
    contract_abi = json.load(f)

contract = web3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=contract_abi
)

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
                event_hash = args["eventHash"].hex() if hasattr(args["eventHash"], "hex") else str(args["eventHash"])
                print(f"🔹 New Event → {panel_id} | {event_type} | {fault_type} | {fault_severity} | {action_taken}")
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

if __name__ == "__main__":
    listen_for_events()
