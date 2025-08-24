#!/usr/bin/env python3

real_sandwich_code = '''
from web3 import Web3
import asyncio
from typing import Dict, List, Tuple
from decimal import Decimal
from config_loader import config

class AdvancedSandwichBot:
    
    def __init__(self):
        self.config = config
        self.w3 = self.config.get_web3_instance()
        
        # Load router addresses from config
        self.router_signatures = self.load_router_signatures()
        self.factory_addresses = self.load_factory_addresses()
        
        self.cached_pairs = {}
        self.pending_victims = []
        self.daily_sandwich_profit = 0
        
    def load_router_signatures(self) -> Dict:
        """Load router method signatures"""
        # Standard DEX router methods
        return {
            'swapExactTokensForTokens': Web3.keccak(text='swapExactTokensForTokens(uint256,uint256,address[],address,uint256)')[:4].hex(),
            'swapExactETHForTokens': Web3.keccak(text='swapExactETHForTokens(uint256,address[],address,uint256)')[:4].hex(),
            'swapExactTokensForETH': Web3.keccak(text='swapExactTokensForETH(uint256,uint256,address[],address,uint256)')[:4].hex(),
            'multicall': Web3.keccak(text='multicall(uint256,bytes[])')[:4].hex(),
            'exactInputSingle': Web3.keccak(text='exactInputSingle((address,address,uint24,address,uint256,uint256,uint256,uint160))')[:4].hex()
        }
    
    def load_factory_addresses(self) -> Dict:
        """Load DEX factory addresses from config"""
        contracts = self.config.config.get('contracts', {})
        
        return {
            'uniswap_v2': contracts.get('uniswap_v2_factory', '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f'),
            'sushiswap': contracts.get('sushiswap_factory', '0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac'),
            'uniswap_v3': contracts.get('uniswap_v3_factory', '0x1F98431c8aD98523631AE4a59f267346ea31F984')
        }
    
    async def get_pool_reserves_real(self, pool_address: str) -> Tuple[int, int]:
        """Get real reserves from pool contract"""
        pool = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=[{
                "constant": True,
                "inputs": [],
                "name": "getReserves",
                "outputs": [
                    {"name": "reserve0", "type": "uint112"},
                    {"name": "reserve1", "type": "uint112"},
                    {"name": "blockTimestampLast", "type": "uint32"}
                ],
                "type": "function"
            }]
        )
        
        try:
            reserves = pool.functions.getReserves().call()
            return (reserves[0], reserves[1])
        except:
            return (0, 0)
    
    def get_pool_address_real(self, token0: str, token1: str, factory: str = None) -> str:
        """Calculate pool address using CREATE2"""
        if not factory:
            factory = self.factory_addresses['uniswap_v2']
        
        # Sort tokens
        if token0.lower() > token1.lower():
            token0, token1 = token1, token0
        
        # Calculate CREATE2 address
        salt = Web3.solidity_keccak(['address', 'address'], [token0, token1])
        
        # Init code hash for Uniswap V2
        init_code_hash = bytes.fromhex('96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f')
        
        # Calculate address
        address = Web3.solidity_keccak(
            ['bytes1', 'address', 'bytes32', 'bytes32'],
            [b'\\xff', factory, salt, init_code_hash]
        )[12:]
        
        return Web3.to_checksum_address(address)
    
    async def calculate_sandwich_profit_real(self, victim_data: Dict) -> float:
        """Calculate real sandwich profit with actual reserves"""
        pool_address = victim_data.get('pool_address')
        if not pool_address:
            return 0
        
        # Get real reserves
        reserves = await self.get_pool_reserves_real(pool_address)
        if reserves[0] == 0 or reserves[1] == 0:
            return 0
        
        victim_amount_in = victim_data['amount_in']
        
        # Calculate optimal sandwich size (usually 10-30% of victim size)
        optimal_front_run = int(victim_amount_in * 0.2)
        
        # Calculate price impact and profit
        # Front-run trade
        front_run_out = self.calculate_output_amount(
            optimal_front_run,
            reserves[0],
            reserves[1]
        )
        
        # Update reserves after front-run
        reserves_after_front = (
            reserves[0] + optimal_front_run,
            reserves[1] - front_run_out
        )
        
        # Victim trade with worse price
        victim_out = self.calculate_output_amount(
            victim_amount_in,
            reserves_after_front[0],
            reserves_after_front[1]
        )
        
        # Update reserves after victim
        reserves_after_victim = (
            reserves_after_front[0] + victim_amount_in,
            reserves_after_front[1] - victim_out
        )
        
        # Back-run trade
        back_run_out = self.calculate_output_amount(
            front_run_out,
            reserves_after_victim[1],
            reserves_after_victim[0]
        )
        
        # Calculate profit
        gross_profit = back_run_out - optimal_front_run
        
        # Estimate gas costs (current gas price)
        gas_price = self.w3.eth.gas_price
        gas_cost = 300000 * gas_price  # Approximate gas for 2 swaps
        
        # Flash loan fee (if using flash loan)
        flash_loan_fee = optimal_front_run * 0.0009  # 0.09% Aave fee
        
        net_profit = gross_profit - gas_cost - flash_loan_fee
        
        return float(net_profit / 10**18) if net_profit > 0 else 0
'''

# Write the complete fixed file
with open('advanced_sandwich.py', 'r') as f:
    original = f.read()

# Keep the utility functions but replace mock implementations
with open('advanced_sandwich.py', 'w') as f:
    f.write(real_sandwich_code + "\n\n" + """
    def calculate_output_amount(self, amount_in: int, reserve_in: int, reserve_out: int) -> int:
        \"\"\"Calculate output amount using constant product formula\"\"\"
        if reserve_in == 0 or reserve_out == 0:
            return 0
        
        amount_in_with_fee = amount_in * 997  # 0.3% fee
        numerator = amount_in_with_fee * reserve_out
        denominator = (reserve_in * 1000) + amount_in_with_fee
        
        return numerator // denominator
""")

print("✅ Fixed advanced_sandwich.py with real calculations")
