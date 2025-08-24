from web3 import Web3

w3 = Web3(Web3.HTTPProvider('https://rpc.flashbots.net'))

uni_pair = '0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'

contract = w3.eth.contract(
    address=uni_pair,
    abi=[{"inputs":[],"name":"getReserves","outputs":[{"type":"uint112"},{"type":"uint112"},{"type":"uint32"}],"type":"function"},
         {"inputs":[],"name":"token0","outputs":[{"type":"address"}],"type":"function"}]
)

reserves = contract.functions.getReserves().call()
token0 = contract.functions.token0().call()

weth = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'

if token0.lower() == weth.lower():
    eth_reserve = reserves[0]
    usdc_reserve = reserves[1]
else:
    eth_reserve = reserves[1]
    usdc_reserve = reserves[0]

eth_amount = eth_reserve / 10**18
usdc_amount = usdc_reserve / 10**6

price = usdc_amount / eth_amount

print(f"Uniswap V2 WETH/USDC Pool")
print(f"ETH Reserve: {eth_amount:,.2f} ETH")
print(f"USDC Reserve: ${usdc_amount:,.2f}")
print(f"ETH Price: ${price:,.2f}")
