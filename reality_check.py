from web3 import Web3

w3 = Web3(Web3.HTTPProvider('https://rpc.flashbots.net'))

# Check REAL flash loan availability
aave = w3.eth.contract(
    address='0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2',
    abi=[{"inputs":[{"type":"address"}],"name":"getReserveData","outputs":[{"components":[{"type":"uint256"}],"type":"tuple"}],"type":"function"}]
)

# USDC address
usdc = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'

print("REALITY CHECK")
print("=" * 50)

# Real arbitrage calculation
price_diff = 0.00136  # 0.136%
eth_amount = 1
eth_price = 4766

gross_profit = eth_amount * eth_price * price_diff
print(f"Gross profit from 1 ETH arbitrage: ${gross_profit:.2f}")

# Real costs
gas_price = w3.eth.gas_price / 10**9  # in gwei
gas_used = 300000  # typical for arbitrage
gas_cost_eth = (gas_price * gas_used) / 10**9
gas_cost_usd = gas_cost_eth * eth_price

flash_loan_fee = eth_amount * eth_price * 0.0009  # 0.09% Aave fee
slippage = eth_amount * eth_price * 0.003  # 0.3% slippage

total_costs = gas_cost_usd + flash_loan_fee + slippage

net_profit = gross_profit - total_costs

print(f"\nCosts:")
print(f"  Gas: ${gas_cost_usd:.2f}")
print(f"  Flash loan fee (0.09%): ${flash_loan_fee:.2f}")
print(f"  Slippage (0.3%): ${slippage:.2f}")
print(f"  Total costs: ${total_costs:.2f}")

print(f"\nNet profit: ${net_profit:.2f}")

if net_profit > 0:
    print("✅ Profitable!")
else:
    print("❌ NOT profitable after costs")

# To make $100 profit, you'd need:
min_arb_needed = (100 + total_costs) / (eth_price * eth_amount)
print(f"\nTo make $100 profit, you need {min_arb_needed*100:.2f}% price difference")
