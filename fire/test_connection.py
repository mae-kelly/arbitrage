from web3 import Web3
from dotenv import load_dotenv
import os

load_dotenv('.env')

# Test Web3 connection
rpc_url = f"https://eth-sepolia.g.alchemy.com/v2/{os.getenv('ALCHEMY_API_KEY')}"
w3 = Web3(Web3.HTTPProvider(rpc_url))

print("Testing connections...")
print(f"Web3 connected: {w3.is_connected()}")
print(f"Chain ID: {w3.eth.chain_id}")
print(f"Latest block: {w3.eth.block_number}")
print(f"Wallet address: {os.getenv('WALLET_ADDRESS')}")

# Check wallet balance
wallet = os.getenv('WALLET_ADDRESS')
if wallet:
    balance = w3.eth.get_balance(wallet)
    print(f"Wallet balance: {Web3.from_wei(balance, 'ether')} ETH")
