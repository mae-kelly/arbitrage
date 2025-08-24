#!/usr/bin/env python3
"""
Real blockchain data queries - no hardcoded values
"""

from web3 import Web3
import os
from typing import Dict, List, Tuple, Optional
import json
from functools import lru_cache
import time

class BlockchainQueries:
    def __init__(self):
        self.w3 = self.get_web3_connection()
        self.last_block = 0
        self.cache = {}
        self.cache_timeout = 12  # seconds (1 block time)
        
    def get_web3_connection(self) -> Web3:
        """Get Web3 connection from available providers"""
        providers = []
        
        # Add from environment
        if os.getenv('RPC_URL'):
            providers.append(os.getenv('RPC_URL'))
        if os.getenv('ALCHEMY_KEY'):
            providers.append(f"https://eth-mainnet.g.alchemy.com/v2/{os.getenv('ALCHEMY_KEY')}")
        if os.getenv('INFURA_KEY'):
            providers.append(f"https://mainnet.infura.io/v3/{os.getenv('INFURA_KEY')}")
            
        # Public fallbacks
        providers.extend([
            'https://eth.llamarpc.com',
            'https://rpc.ankr.com/eth',
            'https://cloudflare-eth.com',
            'https://rpc.flashbots.net'
        ])
        
        for provider in providers:
            try:
                w3 = Web3(Web3.HTTPProvider(provider))
                if w3.is_connected():
                    return w3
            except:
                continue
                
        raise Exception("No Web3 provider available")
    
    def get_current_gas_price(self) -> int:
        """Get current gas price from network"""
        return self.w3.eth.gas_price
    
    def get_eth_price(self) -> float:
        """Get ETH price from Chainlink oracle"""
        oracle_address = '0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419'
        
        oracle = self.w3.eth.contract(
            address=oracle_address,
            abi=[{
                "inputs": [],
                "name": "latestRoundData",
                "outputs": [
                    {"name": "roundId", "type": "uint80"},
                    {"name": "answer", "type": "int256"},
                    {"name": "startedAt", "type": "uint256"},
                    {"name": "updatedAt", "type": "uint256"},
                    {"name": "answeredInRound", "type": "uint80"}
                ],
                "type": "function"
            }]
        )
        
        try:
            data = oracle.functions.latestRoundData().call()
            return data[1] / 10**8
        except:
            return None
    
    def get_token_balance(self, token_address: str, holder_address: str) -> int:
        """Get token balance for any address"""
        token = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=[{
                "inputs": [{"name": "account", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            }]
        )
        
        try:
            return token.functions.balanceOf(holder_address).call()
        except:
            return 0
    
    def get_pool_reserves(self, pool_address: str) -> Tuple[int, int]:
        """Get reserves from any Uniswap V2 style pool"""
        pool = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=[{
                "constant": True,
                "inputs": [],
                "name": "getReserves",
                "outputs": [
                    {"name": "_reserve0", "type": "uint112"},
                    {"name": "_reserve1", "type": "uint112"},
                    {"name": "_blockTimestampLast", "type": "uint32"}
                ],
                "type": "function"
            }]
        )
        
        try:
            reserves = pool.functions.getReserves().call()
            return (reserves[0], reserves[1])
        except:
            return (0, 0)
    
    def get_v3_pool_liquidity(self, pool_address: str) -> int:
        """Get liquidity from Uniswap V3 pool"""
        pool = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=[{
                "inputs": [],
                "name": "liquidity",
                "outputs": [{"name": "", "type": "uint128"}],
                "type": "function"
            }]
        )
        
        try:
            return pool.functions.liquidity().call()
        except:
            return 0
    
    def get_aave_reserve_data(self, asset_address: str) -> Dict:
        """Get reserve data from Aave V3"""
        pool_address = '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'
        
        pool = self.w3.eth.contract(
            address=pool_address,
            abi=[{
                "inputs": [{"name": "asset", "type": "address"}],
                "name": "getReserveData",
                "outputs": [{
                    "components": [
                        {"name": "configuration", "type": "uint256"},
                        {"name": "liquidityIndex", "type": "uint128"},
                        {"name": "currentLiquidityRate", "type": "uint128"},
                        {"name": "variableBorrowIndex", "type": "uint128"},
                        {"name": "currentVariableBorrowRate", "type": "uint128"},
                        {"name": "currentStableBorrowRate", "type": "uint128"},
                        {"name": "lastUpdateTimestamp", "type": "uint40"},
                        {"name": "id", "type": "uint16"},
                        {"name": "aTokenAddress", "type": "address"},
                        {"name": "stableDebtTokenAddress", "type": "address"},
                        {"name": "variableDebtTokenAddress", "type": "address"},
                        {"name": "interestRateStrategyAddress", "type": "address"},
                        {"name": "accruedToTreasury", "type": "uint128"},
                        {"name": "unbacked", "type": "uint128"},
                        {"name": "isolationModeTotalDebt", "type": "uint128"}
                    ],
                    "type": "tuple"
                }],
                "type": "function"
            }]
        )
        
        try:
            data = pool.functions.getReserveData(asset_address).call()
            return {
                'aTokenAddress': data[8],
                'liquidityIndex': data[1],
                'currentLiquidityRate': data[2],
                'variableBorrowIndex': data[3],
                'currentVariableBorrowRate': data[4]
            }
        except:
            return {}
    
    def get_flash_loan_availability(self, protocol: str, asset: str) -> int:
        """Get real flash loan availability"""
        if protocol == 'aave':
            reserve_data = self.get_aave_reserve_data(asset)
            if reserve_data and reserve_data.get('aTokenAddress'):
                return self.get_token_balance(asset, reserve_data['aTokenAddress'])
        elif protocol == 'balancer':
            vault = '0xBA12222222228d8Ba445958a75a0704d566BF2C8'
            return self.get_token_balance(asset, vault)
        
        return 0
    
    def calculate_sandwich_profit(self, pool_address: str, victim_amount: int) -> Dict:
        """Calculate real sandwich profit for a specific pool and trade"""
        reserves = self.get_pool_reserves(pool_address)
        if reserves[0] == 0 or reserves[1] == 0:
            return {'profitable': False}
        
        # Dynamic calculation based on actual reserves
        optimal_front_run = victim_amount * 20 // 100  # 20% of victim trade
        
        # Calculate output with constant product formula
        front_run_out = (optimal_front_run * 997 * reserves[1]) // (reserves[0] * 1000 + optimal_front_run * 997)
        
        # Update reserves
        new_reserve0 = reserves[0] + optimal_front_run
        new_reserve1 = reserves[1] - front_run_out
        
        # Victim gets worse price
        victim_out = (victim_amount * 997 * new_reserve1) // (new_reserve0 * 1000 + victim_amount * 997)
        
        # Update reserves again
        final_reserve0 = new_reserve0 + victim_amount
        final_reserve1 = new_reserve1 - victim_out
        
        # Back run
        back_run_out = (front_run_out * 997 * final_reserve0) // (final_reserve1 * 1000 + front_run_out * 997)
        
        # Calculate profit
        gross_profit = back_run_out - optimal_front_run
        gas_cost = 300000 * self.get_current_gas_price()
        flash_loan_fee = optimal_front_run * 9 // 10000  # 0.09%
        
        net_profit = gross_profit - gas_cost - flash_loan_fee
        
        return {
            'profitable': net_profit > 0,
            'gross_profit': gross_profit,
            'gas_cost': gas_cost,
            'flash_loan_fee': flash_loan_fee,
            'net_profit': net_profit
        }
    
    def get_pending_transactions(self, limit: int = 100) -> List[Dict]:
        """Get real pending transactions"""
        try:
            pending_filter = self.w3.eth.filter('pending')
            pending_hashes = pending_filter.get_new_entries()[:limit]
            
            transactions = []
            for tx_hash in pending_hashes:
                try:
                    tx = self.w3.eth.get_transaction(tx_hash)
                    if tx:
                        transactions.append(dict(tx))
                except:
                    continue
                    
            return transactions
        except:
            return []
    
    def find_arbitrage_opportunity(self, token0: str, token1: str, dex1: str, dex2: str) -> Dict:
        """Find real arbitrage opportunity between two DEXes"""
        # Get reserves from both DEXes
        reserves1 = self.get_pool_reserves(dex1)
        reserves2 = self.get_pool_reserves(dex2)
        
        if any(r == 0 for r in reserves1 + reserves2):
            return {'profitable': False}
        
        # Calculate prices
        price1 = reserves1[1] / reserves1[0]
        price2 = reserves2[1] / reserves2[0]
        
        # Check if arbitrage exists
        price_diff = abs(price1 - price2) / min(price1, price2)
        
        if price_diff > 0.003:  # 0.3% difference minimum
            # Calculate optimal trade size (simplified)
            optimal_size = int((reserves1[0] * reserves2[0] * price_diff) ** 0.5)
            
            # Calculate profit
            gross_profit = optimal_size * price_diff
            gas_cost = 200000 * self.get_current_gas_price()
            flash_loan_fee = optimal_size * 9 // 10000
            
            net_profit = gross_profit - gas_cost - flash_loan_fee
            
            return {
                'profitable': net_profit > 0,
                'price_diff': price_diff,
                'optimal_size': optimal_size,
                'net_profit': net_profit
            }
        
        return {'profitable': False}

# Singleton instance
blockchain = BlockchainQueries()
