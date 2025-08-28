# strategies/liquidation_hunter.py

from typing import Dict, Optional, List
from web3 import Web3
from .base_strategy import BaseStrategy
from config import Config
import json

class LiquidationHunterStrategy(BaseStrategy):
    def __init__(self, dex_client, discord_notifier):
        super().__init__("Liquidation Hunter")
        self.dex = dex_client
        self.discord = discord_notifier
        self.config = Config()
        self.monitored_positions = []
        
    async def initialize(self):
        self.aave_pool_address = '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'
        self.compound_comptroller = '0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B'
        
        with open('abi/aave_pool.json', 'r') as f:
            self.aave_pool_abi = json.load(f)
        
        with open('abi/compound_comptroller.json', 'r') as f:
            self.compound_abi = json.load(f)
        
        self.health_factor_threshold = 1.05
        self.min_liquidation_bonus = 0.05
    
    async def execute(self) -> Optional[Dict]:
        if not self.should_execute():
            return None
        
        await self.update_monitored_positions()
        
        for position in self.monitored_positions:
            if await self.is_liquidatable(position):
                result = await self.execute_liquidation(position)
                if result:
                    self.update_metrics(result)
                    return result
        
        return None
    
    async def update_monitored_positions(self):
        aave_positions = await self.get_aave_positions()
        compound_positions = await self.get_compound_positions()
        
        self.monitored_positions = aave_positions + compound_positions
    
    async def get_aave_positions(self) -> List[Dict]:
        positions = []
        
        w3 = self.dex.w3
        aave_pool = w3.eth.contract(address=self.aave_pool_address, abi=self.aave_pool_abi)
        
        try:
            recent_events = aave_pool.events.Borrow().get_logs(fromBlock=w3.eth.block_number - 1000)
            
            unique_users = set()
            for event in recent_events:
                unique_users.add(event['args']['user'])
            
            for user in list(unique_users)[:50]:
                user_data = aave_pool.functions.getUserAccountData(user).call()
                
                health_factor = user_data[5] / 10**18 if user_data[5] > 0 else float('inf')
                
                if health_factor < self.health_factor_threshold * 1.5:
                    positions.append({
                        'protocol': 'aave',
                        'user': user,
                        'health_factor': health_factor,
                        'total_collateral_base': user_data[0],
                        'total_debt_base': user_data[1],
                        'available_borrow_base': user_data[2],
                        'liquidation_threshold': user_data[3],
                        'ltv': user_data[4]
                    })
            
        except Exception as e:
            print(f"Error getting Aave positions: {e}")
        
        return positions
    
    async def get_compound_positions(self) -> List[Dict]:
        positions = []
        
        w3 = self.dex.w3
        comptroller = w3.eth.contract(address=self.compound_comptroller, abi=self.compound_abi)
        
        try:
            markets = comptroller.functions.getAllMarkets().call()
            
            for market in markets[:10]:
                with open('abi/compound_ctoken.json', 'r') as f:
                    ctoken_abi = json.load(f)
                
                ctoken = w3.eth.contract(address=market, abi=ctoken_abi)
                
                recent_borrows = ctoken.events.Borrow().get_logs(fromBlock=w3.eth.block_number - 1000)
                
                for event in recent_borrows[:20]:
                    borrower = event['args']['borrower']
                    
                    account_liquidity = comptroller.functions.getAccountLiquidity(borrower).call()
                    
                    if account_liquidity[1] == 0 and account_liquidity[2] > 0:
                        positions.append({
                            'protocol': 'compound',
                            'user': borrower,
                            'market': market,
                            'shortfall': account_liquidity[2],
                            'liquidity': account_liquidity[1]
                        })
                
        except Exception as e:
            print(f"Error getting Compound positions: {e}")
        
        return positions
    
    async def is_liquidatable(self, position: Dict) -> bool:
        if position['protocol'] == 'aave':
            return position['health_factor'] < 1.0
        elif position['protocol'] == 'compound':
            return position['shortfall'] > 0
        return False
    
    async def execute_liquidation(self, position: Dict) -> Dict:
        try:
            if position['protocol'] == 'aave':
                return await self.execute_aave_liquidation(position)
            elif position['protocol'] == 'compound':
                return await self.execute_compound_liquidation(position)
            
        except Exception as e:
            await self.discord.send_error_alert(f"Liquidation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def execute_aave_liquidation(self, position: Dict) -> Dict:
        w3 = self.dex.w3
        aave_pool = w3.eth.contract(address=self.aave_pool_address, abi=self.aave_pool_abi)
        
        user_reserves = aave_pool.functions.getUserConfiguration(position['user']).call()
        
        collateral_asset = self.config.TOKENS['WETH']
        debt_asset = self.config.TOKENS['USDC']
        
        max_liquidatable = position['total_debt_base'] // 2
        
        tx = aave_pool.functions.liquidationCall(
            collateral_asset,
            debt_asset,
            position['user'],
            max_liquidatable,
            False
        ).build_transaction({
            'from': self.config.WALLET_ADDRESS,
            'gas': 500000,
            'gasPrice': await self.dex.get_gas_price_wei(),
            'nonce': w3.eth.get_transaction_count(self.config.WALLET_ADDRESS)
        })
        
        signed_tx = self.dex.account.sign_transaction(tx)
        tx_hash = await self.dex.rpc.send_transaction(signed_tx.rawTransaction)
        
        receipt = await self.dex.rpc.wait_for_transaction(tx_hash)
        
        if receipt['status'] == 1:
            profit = self.calculate_liquidation_profit(max_liquidatable, 0.05)
            
            return {
                'success': True,
                'type': 'Aave Liquidation',
                'user': position['user'],
                'amount': max_liquidatable,
                'profit': profit,
                'tx_hash': tx_hash
            }
        
        return {
            'success': False,
            'error': 'Transaction failed'
        }
    
    async def execute_compound_liquidation(self, position: Dict) -> Dict:
        w3 = self.dex.w3
        
        with open('abi/compound_ctoken.json', 'r') as f:
            ctoken_abi = json.load(f)
        
        ctoken = w3.eth.contract(address=position['market'], abi=ctoken_abi)
        
        borrow_balance = ctoken.functions.borrowBalanceStored(position['user']).call()
        max_liquidate = borrow_balance // 2
        
        tx = ctoken.functions.liquidateBorrow(
            position['user'],
            max_liquidate,
            position['market']
        ).build_transaction({
            'from': self.config.WALLET_ADDRESS,
            'gas': 500000,
            'gasPrice': await self.dex.get_gas_price_wei(),
            'nonce': w3.eth.get_transaction_count(self.config.WALLET_ADDRESS),
            'value': max_liquidate if 'CEther' in str(position['market']) else 0
        })
        
        signed_tx = self.dex.account.sign_transaction(tx)
        tx_hash = await self.dex.rpc.send_transaction(signed_tx.rawTransaction)
        
        receipt = await self.dex.rpc.wait_for_transaction(tx_hash)
        
        if receipt['status'] == 1:
            profit = self.calculate_liquidation_profit(max_liquidate, 0.08)
            
            return {
                'success': True,
                'type': 'Compound Liquidation',
                'user': position['user'],
                'amount': max_liquidate,
                'profit': profit,
                'tx_hash': tx_hash
            }
        
        return {
            'success': False,
            'error': 'Transaction failed'
        }
    
    def calculate_liquidation_profit(self, amount: int, bonus_percentage: float) -> float:
        amount_eth = Web3.from_wei(amount, 'ether')
        bonus = amount_eth * bonus_percentage
        gas_cost = 0.02
        
        return (bonus - gas_cost) * 2000
    
    async def cleanup(self):
        pass