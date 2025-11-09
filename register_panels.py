import os
from web3 import Web3
from eth_account import Account

# -------------------------------------------------------------------
# Configuration (all sensitive values from environment variables)
# -------------------------------------------------------------------
INFURA_URL = os.getenv("INFURA_URL")              # your Infura RPC endpoint
CONTRACT_ADDRESS = Web3.to_checksum_address(os.getenv("CONTRACT_ADDRESS"))
ABI_PATH = os.getenv("ABI_PATH", "contract_abi.json")
PANELS_DIR = os.getenv("PANELS_DIR", "panels")
CHAIN_ID = int(os.getenv("CHAIN_ID", "11155111")) # Sepolia default

# Sensitive keys and addresses
PRIVATE_KEY = os.getenv("PRIVATE_KEY")            # Metamask private key (oracle)
ORACLE_ADDRESS = os.getenv("ORACLE_ADDRESS")      # public oracle wallet address
ADMIN_ADDRESS = os.getenv("ADMIN_ADDRESS")        # contract owner/admin address

# -------------------------------------------------------------------
# Web3 setup
# -------------------------------------------------------------------
w3 = Web3(Web3.HTTPProvider(INFURA_URL))
if not w3.is_connected():
    raise RuntimeError("Web3 not connected to RPC")

with open(ABI_PATH, "r", encoding="utf-8") as f:
    CONTRACT_ABI = json.load(f)

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

# Account object from private key (used only when signing transactions)
account = Account.from_key(PRIVATE_KEY)
print(f"🔑 Oracle account loaded: {account.address}")

