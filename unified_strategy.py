from blockchain_queries import blockchain
from config_loader import config
from contract_registry import ContractRegistry
from web3 import Web3
from typing import Dict, List, Tuple
import asyncio
import aiohttp
import numpy as np

class UnifiedStrategy:
    def __init__(self, w3):
        self.w3 = w3
        
        self.dex_addresses = {
            'uniswap_v2_router': config.config['contracts'].get('contract_name', '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
            'uniswap_v3_router': config.config['contracts'].get('contract_name', '0xE592427A0AEce92De3Edee1F18E0157C05861564'),
            'sushiswap_router': config.config['contracts'].get('contract_name', '0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            'curve_3pool': config.config['contracts'].get('contract_name', '0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7'),
            'balancer_vault': config.config['contracts'].get('contract_name', '0xBA12222222228d8Ba445958a75a0704d566BF2C8')
        }
        
        self.lending_protocols = {
            'aave_v3': config.config['contracts'].get('contract_name', '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'),
            'compound': config.config['contracts'].get('contract_name', '0xc3d688B66703497DAA19211EEdff47f25384cdc3'),
            'maker': config.config['contracts'].get('contract_name', '0x60744434d6339a6B27d73d9Eda62b6F66a0a04FA')
        }
        
        self.oracle_addresses = {
            'chainlink_eth': config.config['contracts'].get('contract_name', '0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419'),
            'chainlink_btc': config.config['contracts'].get('contract_name', '0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c'),
            'chainlink_usdc': config.config['contracts'].get('contract_name', '0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6')
        }
        
        self.bridge_contracts = {
            'stargate': config.config['contracts'].get('contract_name', '0x8731d54E9D02c286767d56ac03e8037C07e01e98'),
            'across': config.config['contracts'].get('contract_name', '0x4D9079Bb4165aeb4084c526a32695dCfd2F77381'),
            'hop': config.config['contracts'].get('contract_name', '0x3666f603Cc164936C1b87e207F36BEBa4AC5f18a')
        }
    
    async def execute_sandwich(self, target_tx: Dict, capital: int) -> Dict:
        pool = self.identify_target_pool(target_tx)
        token_in, token_out = self.parse_swap_tokens(target_tx)
        amount_in = int(target_tx['value'])
        
        reserves_before = await self.get_reserves(pool)
        price_impact = self.calculate_price_impact(amount_in, reserves_before)
        
        front_run_amount = int(amount_in * 0.3)
        
        front_run_output = self.calculate_output(front_run_amount, reserves_before)
        
        reserves_after_front = self.update_reserves(
            reserves_before, 
            front_run_amount, 
            front_run_output
        )
        
        victim_output = self.calculate_output(amount_in, reserves_after_front)
        
        reserves_after_victim = self.update_reserves(
            reserves_after_front,
            amount_in,
            victim_output
        )
        
        back_run_output = self.calculate_output(
            front_run_output,
            reserves_after_victim,
            reverse=True
        )
        
        profit = back_run_output - front_run_amount
        gas_cost = 300000 * self.w3.eth.gas_price
        net_profit = profit - gas_cost
        
        return {
            'type': 'sandwich',
            'profit': net_profit,
            'front_run': front_run_amount,
            'back_run': back_run_output,
            'gas_used': 300000
        }
    
    async def execute_liquidation(self, position: Dict) -> Dict:
        protocol = position['protocol']
        user = position['user']
        collateral_asset = position['collateral_asset']
        debt_asset = position['debt_asset']
        debt_to_cover = position['debt_to_cover']
        
        liquidation_bonus = self.get_liquidation_bonus(protocol)
        collateral_to_receive = debt_to_cover * (1 + liquidation_bonus)
        
        gross_profit = debt_to_cover * liquidation_bonus
        gas_cost = 400000 * self.w3.eth.gas_price
        flash_loan_fee = debt_to_cover * 0.0009
        
        net_profit = gross_profit - gas_cost - flash_loan_fee
        
        return {
            'type': 'liquidation',
            'profit': net_profit,
            'debt_covered': debt_to_cover,
            'collateral_received': collateral_to_receive,
            'gas_used': 400000
        }
    
    async def execute_arbitrage(self, path: List[Dict], capital: int) -> Dict:
        current_amount = capital
        
        for i, hop in enumerate(path):
            pool = hop['pool']
            token_in = hop['token_in']
            token_out = hop['token_out']
            
            reserves = await self.get_reserves(pool)
            output = self.calculate_output(current_amount, reserves)
            
            current_amount = output
        
        gross_profit = current_amount - capital
        
        gas_cost = len(path) * 150000 * self.w3.eth.gas_price
        flash_loan_fee = capital * 0.0009
        slippage = gross_profit * 0.003
        
        net_profit = gross_profit - gas_cost - flash_loan_fee - slippage
        
        return {
            'type': 'arbitrage',
            'profit': net_profit,
            'path_length': len(path),
            'capital_used': capital,
            'gas_used': len(path) * 150000
        }
    
    async def execute_oracle_arbitrage(self, divergence: Dict) -> Dict:
        oracle_price = divergence['oracle_price']
        dex_price = divergence['dex_price']
        capital = divergence['capital_required']
        
        price_diff = abs(dex_price - oracle_price) / oracle_price
        
        if oracle_price < dex_price:
            borrow_amount = capital
            sell_amount = capital
            profit_per_unit = dex_price - oracle_price
        else:
            buy_amount = capital
            deposit_amount = capital
            profit_per_unit = oracle_price - dex_price
        
        gross_profit = capital * price_diff
        
        gas_cost = 500000 * self.w3.eth.gas_price
        flash_loan_fee = capital * 0.0009
        slippage = gross_profit * 0.05
        
        net_profit = gross_profit - gas_cost - flash_loan_fee - slippage
        
        return {
            'type': 'oracle_arbitrage',
            'profit': net_profit,
            'divergence': price_diff,
            'capital_used': capital,
            'gas_used': 500000
        }
    
    async def execute_bridge_arbitrage(self, opportunity: Dict) -> Dict:
        source_chain = opportunity['source_chain']
        target_chain = opportunity['target_chain']
        capital = opportunity['capital_required']
        price_diff = opportunity['price_diff']
        
        source_price = await self.get_chain_price(source_chain)
        target_price = await self.get_chain_price(target_chain)
        
        if source_price < target_price:
            buy_on = source_chain
            sell_on = target_chain
        else:
            buy_on = target_chain
            sell_on = source_chain
        
        gross_profit = capital * price_diff
        
        gas_cost_source = 200000 * 30 * 10**9
        gas_cost_target = 200000 * 5 * 10**9
        bridge_fee = capital * 0.001
        flash_loan_fee = capital * 0.0009
        slippage = gross_profit * 0.01
        
        total_costs = gas_cost_source + gas_cost_target + bridge_fee + flash_loan_fee + slippage
        net_profit = gross_profit - total_costs
        
        return {
            'type': 'bridge_arbitrage',
            'profit': net_profit,
            'source_chain': buy_on,
            'target_chain': sell_on,
            'price_diff': price_diff,
            'gas_used': 400000
        }
    
    async def execute_multi_strategy(self, opportunities: List[Dict], total_capital: int) -> Dict:
        results = []
        capital_per_strategy = total_capital // len(opportunities)
        
        tasks = []
        for opp in opportunities:
            if opp['type'] == 'sandwich':
                task = self.execute_sandwich(opp['target_transaction'], capital_per_strategy)
            elif opp['type'] == 'liquidation':
                task = self.execute_liquidation(opp)
            elif opp['type'] == 'arbitrage':
                task = self.execute_arbitrage(opp['path'], capital_per_strategy)
            elif opp['type'] == 'oracle':
                task = self.execute_oracle_arbitrage(opp)
            elif opp['type'] == 'bridge':
                task = self.execute_bridge_arbitrage(opp)
            else:
                continue
            
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        total_profit = sum(r['profit'] for r in results)
        total_gas = sum(r['gas_used'] for r in results)
        
        return {
            'type': 'multi_strategy',
            'profit': total_profit,
            'strategies_executed': len(results),
            'gas_used': total_gas,
            'individual_results': results
        }
    
    def identify_target_pool(self, tx: Dict) -> str:
        to_address = tx.get('to', '').lower()
        
        if to_address == self.dex_addresses['uniswap_v2_router'].lower():
            return config.config['contracts'].get('contract_name', '0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc')
        elif to_address == self.dex_addresses['sushiswap_router'].lower():
            return config.config['contracts'].get('contract_name', '0x397FF1542f962076d0BFE58eA045FfA2d347ACa0')
        else:
            return config.config['contracts'].get('contract_name', '0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640')
    
    def parse_swap_tokens(self, tx: Dict) -> Tuple[str, str]:
        return (config.config['contracts'].get('contract_name', '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                config.config['contracts'].get('contract_name', '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'))
    
    
    async def get_reserves(self, pool: str) -> Tuple[int, int]:
        """Get real reserves from pool"""
        try:
            pool_contract = self.w3.eth.contract(
                address=Web3.toChecksumAddress(pool),
                abi=[
                    {"constant":True,"inputs":[],"name":"getReserves","outputs":[{"name":"_reserve0","type":"uint112"},{"name":"_reserve1","type":"uint112"},{"name":"_blockTimestampLast","type":"uint32"}],"type":"function"}
                ]
            )
            reserves = pool_contract.functions.getReserves().call()
            return (reserves[0], reserves[1])
        except:
            # Fallback for V3 pools
            try:
                pool_contract = self.w3.eth.contract(
                    address=Web3.toChecksumAddress(pool),
                    abi=[{"inputs":[],"name":"liquidity","outputs":[{"name":"","type":"uint128"}],"type":"function"}]
                )
                liquidity = pool_contract.functions.liquidity().call()
                # Approximate reserves for V3
                return (liquidity // 2, liquidity // 2)
            except:
                return blockchain.get_pool_reserves(pool_address)

    
    def calculate_price_impact(self, amount_in: int, reserves: Tuple[int, int]) -> float:
        return (amount_in / reserves[0]) ** 0.5
    
    def calculate_output(self, amount_in: int, reserves: Tuple[int, int], reverse: bool = False) -> int:
        if reverse:
            reserve_in, reserve_out = reserves[1], reserves[0]
        else:
            reserve_in, reserve_out = reserves[0], reserves[1]
        
        amount_in_with_fee = amount_in * 997
        numerator = amount_in_with_fee * reserve_out
        denominator = reserve_in * 1000 + amount_in_with_fee
        
        return numerator // denominator
    
    def update_reserves(self, reserves: Tuple[int, int], amount_in: int, amount_out: int) -> Tuple[int, int]:
        return (reserves[0] + amount_in, reserves[1] - amount_out)
    
    def get_liquidation_bonus(self, protocol: str) -> float:
        bonuses = {
            'aave_v3': 0.05,
            'compound': 0.08,
            'maker': 0.13
        }
        return bonuses.get(protocol, 0.05)
    
    
    async def get_chain_price(self, chain: str) -> float:
        """Get real price from chain"""
        oracle_addresses = {
            'ethereum': config.config['contracts'].get('contract_name', '0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419'),
            'bsc': config.config['contracts'].get('contract_name', '0x0567F2323251f0Aab15c8dFb1967E4e8A7D42aeE'),
            'polygon': config.config['contracts'].get('contract_name', '0xAB594600376Ec9fD91F8e885dADF0CE036862dE0'),
            'arbitrum': config.config['contracts'].get('contract_name', '0x639Fe6ab55C921f74e7fac1ee960C0B6293ba612')
        }
        
        try:
            if chain not in oracle_addresses:
                return 3200.0
            
            # Use appropriate Web3 instance for chain
            w3 = self.get_chain_w3(chain)
            
            oracle = w3.eth.contract(
                address=oracle_addresses[chain],
                abi=[{"inputs":[],"name":"latestAnswer","outputs":[{"name":"","type":"int256"}],"type":"function"}]
            )
            
            price = oracle.functions.latestAnswer().call() / 10**8
            return float(price)
        except:
            return 3200.0
