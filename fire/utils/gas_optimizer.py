# utils/gas_optimizer.py

from typing import Dict, List, Optional
from web3 import Web3
import time
from config import Config

class GasOptimizer:
    def __init__(self, rpc_manager):
        self.rpc = rpc_manager
        self.config = Config()
        self.fee_history = []
        self.base_fee_cache = {}
        self.cache_ttl = 12
        
    async def get_optimal_gas_price(self, urgency: str = 'standard') -> Dict:
        w3 = self.rpc.get_w3()
        
        latest_block = w3.eth.get_block('latest')
        base_fee = latest_block.get('baseFeePerGas', 0)
        
        fee_history = w3.eth.fee_history(10, 'latest', [25, 50, 75])
        
        priority_fees = fee_history['reward']
        
        if urgency == 'fast':
            priority_fee = max([block[2] for block in priority_fees])
            max_fee = base_fee * 2 + priority_fee
        elif urgency == 'slow':
            priority_fee = min([block[0] for block in priority_fees])
            max_fee = int(base_fee * 1.5 + priority_fee)
        else:
            priority_fee = sum([block[1] for block in priority_fees]) // len(priority_fees)
            max_fee = int(base_fee * 1.8 + priority_fee)
        
        max_fee = min(max_fee, Web3.to_wei(self.config.MAX_GAS_PRICE_GWEI, 'gwei'))
        
        return {
            'maxFeePerGas': max_fee,
            'maxPriorityFeePerGas': priority_fee,
            'baseFee': base_fee
        }
    
    async def estimate_transaction_cost(self, gas_limit: int, urgency: str = 'standard') -> float:
        gas_price = await self.get_optimal_gas_price(urgency)
        
        total_gas_wei = gas_limit * gas_price['maxFeePerGas']
        total_gas_eth = Web3.from_wei(total_gas_wei, 'ether')
        
        eth_price = 2000
        
        return float(total_gas_eth) * eth_price
    
    async def should_execute_based_on_gas(self, expected_profit: float, gas_limit: int) -> bool:
        estimated_cost = await self.estimate_transaction_cost(gas_limit)
        
        return expected_profit > estimated_cost * 1.5
    
    async def get_gas_price_percentiles(self) -> Dict:
        w3 = self.rpc.get_w3()
        
        fee_history = w3.eth.fee_history(100, 'latest', [10, 25, 50, 75, 90])
        
        percentiles = {
            'p10': [],
            'p25': [],
            'p50': [],
            'p75': [],
            'p90': []
        }
        
        for block_fees in fee_history['reward']:
            if block_fees:
                percentiles['p10'].append(block_fees[0])
                percentiles['p25'].append(block_fees[1])
                percentiles['p50'].append(block_fees[2])
                percentiles['p75'].append(block_fees[3])
                percentiles['p90'].append(block_fees[4])
        
        return {
            'p10': sum(percentiles['p10']) // len(percentiles['p10']) if percentiles['p10'] else 0,
            'p25': sum(percentiles['p25']) // len(percentiles['p25']) if percentiles['p25'] else 0,
            'p50': sum(percentiles['p50']) // len(percentiles['p50']) if percentiles['p50'] else 0,
            'p75': sum(percentiles['p75']) // len(percentiles['p75']) if percentiles['p75'] else 0,
            'p90': sum(percentiles['p90']) // len(percentiles['p90']) if percentiles['p90'] else 0,
        }
    
    def calculate_eip1559_gas(self, base_fee: int, priority_fee: int, multiplier: float = 1.5) -> Dict:
        max_fee = int(base_fee * multiplier + priority_fee)
        
        return {
            'maxFeePerGas': max_fee,
            'maxPriorityFeePerGas': priority_fee
        }
    
    async def get_network_congestion(self) -> str:
        w3 = self.rpc.get_w3()
        
        latest_block = w3.eth.get_block('latest')
        gas_used_ratio = latest_block['gasUsed'] / latest_block['gasLimit']
        
        if gas_used_ratio > 0.9:
            return 'high'
        elif gas_used_ratio > 0.7:
            return 'medium'
        else:
            return 'low'
    
    async def wait_for_optimal_gas(self, max_wait: int = 60, target_gwei: int = 50):
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            current_gas = await self.get_optimal_gas_price('standard')
            current_gwei = Web3.from_wei(current_gas['maxFeePerGas'], 'gwei')
            
            if current_gwei <= target_gwei:
                return True
            
            await asyncio.sleep(5)
        
        return False
    
    async def build_flashbots_bundle(self, transactions: List[Dict]) -> Dict:
        bundle = {
            'version': '0.1.0',
            'inclusion': {
                'block': None,
                'maxBlock': None
            },
            'body': []
        }
        
        w3 = self.rpc.get_w3()
        current_block = w3.eth.block_number
        
        bundle['inclusion']['block'] = hex(current_block + 1)
        bundle['inclusion']['maxBlock'] = hex(current_block + 10)
        
        for tx in transactions:
            if 'raw' in tx:
                bundle['body'].append({
                    'tx': tx['raw']
                })
            else:
                bundle['body'].append({
                    'tx': tx['signedTransaction'].hex() if hasattr(tx['signedTransaction'], 'hex') else tx['signedTransaction']
                })
        
        return bundle