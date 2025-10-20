import os, json, time
from web3 import Web3
from dotenv import load_dotenv
from oracle_automation import process_and_anchor

load_dotenv()

# Real Sepolia WebSocket endpoint and addresses
INFURA_WS = "wss://sepolia.infura.io/ws/v3/57ea67cde27f45f9af5a69bdc5c92332"
CONTRACT_ADDRESS = Web3.to_checksum_address("0x59B649856d8c5Fb6991d30a345f0b923eA91a3f7")
WALLET_ADDRESS = "0xb8935eBEb1dA663C187fc9090b77E1972A909e12"

# Web3 v7: LegacyWebSocketProvider still works, but you can also use WebsocketProvider
web3 = Web3(Web3.WebsocketProvider(INFURA_WS, websocket_timeout=30))

with open("contract_abi.json", "r", encoding="utf-8") as f:
    contract_abi = json.load(f)

contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

def listen_for_events():
    print("👂 Worker listening for PanelEventAdded events in real time...")
    # ✅ Web3 v7 syntax
    event_filter = contract.events.PanelEventAdded.create_filter(from_block=0)

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
                validated_by = args["validatedBy"]
                timestamp = args["timestamp"]

                print(f"🔹 New Event → {panel_id} | {event_type} | {fault_type} | {fault_severity} | {action_taken} | {validated_by} | {timestamp}")

                process_and_anchor(
                    panel_id=panel_id,
                    event_type=event_type,
                    fault_type=fault_type,
                    fault_severity=fault_severity,
                    action_taken=action_taken,
                    event_hash=event_hash,
                    validated_by=validated_by,
                    timestamp=timestamp
                )
        except Exception as e:
            print(f"⚠️ Worker error: {type(e).__name__}: {e}")
            time.sleep(5)
        time.sleep(2)

if __name__ == "__main__":
    listen_for_events()
