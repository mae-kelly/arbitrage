from web3 import Web3
import json

print("Testing real blockchain connection...")

endpoints = [
    'https://rpc.ankr.com/eth',
    'https://cloudflare-eth.com',
    'https://rpc.flashbots.net',
    'https://eth.llamarpc.com'
]

for endpoint in endpoints:
    try:
        w3 = Web3(Web3.HTTPProvider(endpoint))
        if w3.is_connected():
            print(f"✅ Connected via {endpoint}")
            print(f"   Block: {w3.eth.block_number:,}")
            print(f"   Gas: {w3.eth.gas_price / 10**9:.1f} gwei")
            
            uni_pair = w3.eth.contract(
                address='0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc',
                abi=[{"constant":True,"inputs":[],"name":"getReserves","outputs":[{"name":"","type":"uint112"},{"name":"","type":"uint112"},{"name":"","type":"uint32"}],"type":"function"}]
            )
            reserves = uni_pair.functions.getReserves().call()
            price = (reserves[1] / 10**6) / (reserves[0] / 10**18)
            print(f"   ETH/USDC price: ${price:.2f}")
            break
    except Exception as e:
        print(f"❌ Failed {endpoint}: {e}")

print("\nChecking wallet...")
try:
    with open('.keys.json', 'r') as f:
        keys = json.load(f)
        print(f"✅ Wallet: {keys['main']['address']}")
        balance = w3.eth.get_balance(keys['main']['address'])
        print(f"   Balance: {balance / 10**18:.6f} ETH")
except:
    print("❌ No wallet found")
