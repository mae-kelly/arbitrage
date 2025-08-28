# strategies/dex_arbitrage.py

from typing import Dict, Optional, List
from web3 import Web3
from .base_strategy import BaseStrategy
from config import Config
from core.flash_loan import FlashLoanExecutor

class DEXArbitrageStrategy(BaseStrategy):
    def __init__(self, dex_client, discord_notifier):
        super().__init__("DEX-to-DEX Arbitrage")
        self.dex = dex_client
        self.discord = discord_notifier
        self.config = Config()
        self.flash_loan = FlashLoanExecutor(dex_client.rpc, dex_client)
        self.min_profit_wei = Web3.to_wei(0.01, 'ether')
        
    async def initialize(self):
        await self.flash_loan.initialize()
        
        self.dex_pairs = [
            ('uniswap_v2', 'sushiswap'),
            ('uniswap_v3', 'uniswap_v2'),
            ('uniswap_v3', 'sushiswap')
        ]
        
        self.token_pairs = [
            (self.config.TOKENS['WETH'], self.config.TOKENS['USDC']),
            (self.config.TOKENS['WETH'], self.config.TOKENS['USDT']),
            (self.config.TOKENS['USDC'], self.config.TOKENS['USDT'])
        ]
    
    async def execute(self) -> Optional[Dict]:
        if not self.should_execute():
            return None
        
        opportunities = await self.find_all_opportunities()
        
        if opportunities:
            best_opportunity = max(opportunities, key=lambda x: x['expected_profit'])
            
            if best_opportunity['expected_profit'] > self.config.MIN_PROFIT_USD:
                result = await self.execute_arbitrage(best_opportunity)
                if result:
                    self.update_metrics(result)
                    return result
        
        return None
    
    async def find_all_opportunities(self) -> List[Dict]:
        opportunities = []
        
        for dex_a, dex_b in self.dex_pairs:
            for token_a, token_b in self.token_pairs:
                opp = await self.find_arbitrage_opportunity(dex_a, dex_b, token_a, token_b)
                if opp:
                    opportunities.append(opp)
        
        return opportunities
    
    async def find_arbitrage_opportunity(self, dex_a: str, dex_b: str, token_a: str, token_b: str) -> Optional[Dict]:
        try:
            if dex_a == 'uniswap_v3':
                price_a = await self.dex.get_pool_price(token_a, token_b, 3000)
            else:
                reserves_a = await self.dex.get_reserves_uniswap_v2(token_a, token_b)
                if reserves_a[0] == 0 or reserves_a[1] == 0:
                    return None
                price_a = reserves_a[1] / reserves_a[0]
            
            if dex_b == 'uniswap_v3':
                price_b = await self.dex.get_pool_price(token_a, token_b, 3000)
            else:
                reserves_b = await self.get_reserves_for_dex(dex_b, token_a, token_b)
                if reserves_b[0] == 0 or reserves_b[1] == 0:
                    return None
                price_b = reserves_b[1] / reserves_b[0]
            
            if price_a == 0 or price_b == 0:
                return None
            
            spread = abs(price_a - price_b) / min(price_a, price_b)
            
            if spread > 0.005:
                if price_a < price_b:
                    return {
                        'buy_dex': dex_a,
                        'sell_dex': dex_b,
                        'token_in': token_a,
                        'token_out': token_b,
                        'price_buy': price_a,
                        'price_sell': price_b,
                        'spread': spread,
                        'expected_profit': self.calculate_expected_profit(1, price_a, price_b)
                    }
                else:
                    return {
                        'buy_dex': dex_b,
                        'sell_dex': dex_a,
                        'token_in': token_a,
                        'token_out': token_b,
                        'price_buy': price_b,
                        'price_sell': price_a,
                        'spread': spread,
                        'expected_profit': self.calculate_expected_profit(1, price_b, price_a)
                    }
            
        except Exception as e:
            print(f"Error finding DEX opportunity: {e}")
        
        return None
    
    async def get_reserves_for_dex(self, dex: str, token_a: str, token_b: str) -> tuple:
        if dex == 'sushiswap':
            factory_address = '0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac'
        else:
            return await self.dex.get_reserves_uniswap_v2(token_a, token_b)
        
        return await self.get_reserves_from_factory(factory_address, token_a, token_b)
    
    async def get_reserves_from_factory(self, factory_address: str, token_a: str, token_b: str) -> tuple:
        w3 = self.dex.w3
        
        with open('abi/uniswap_v2_factory.json', 'r') as f:
            import json
            factory_abi = json.load(f)
        
        factory = w3.eth.contract(address=factory_address, abi=factory_abi)
        pair_address = factory.functions.getPair(token_a, token_b).call()
        
        if pair_address == '0x0000000000000000000000000000000000000000':
            return (0, 0)
        
        with open('abi/uniswap_v2_pair.json', 'r') as f:
            pair_abi = json.load(f)
        
        pair = w3.eth.contract(address=pair_address, abi=pair_abi)
        reserves = pair.functions.getReserves().call()
        token0 = pair.functions.token0().call()
        
        if token0.lower() == token_a.lower():
            return (reserves[0], reserves[1])
        else:
            return (reserves[1], reserves[0])
    
    def calculate_expected_profit(self, amount_eth: float, buy_price: float, sell_price: float) -> float:
        buy_cost = amount_eth * buy_price * 1.003
        sell_revenue = amount_eth * sell_price * 0.997
        gas_cost_usd = 0.01 * 2000
        
        return sell_revenue - buy_cost - gas_cost_usd
    
    async def execute_arbitrage(self, opportunity: Dict) -> Dict:
        try:
            amount_wei = Web3.to_wei(1, 'ether')
            
            flash_loan_params = {
                'expected_profit': opportunity['expected_profit']
            }
            
            simulation = await self.flash_loan.simulate_flash_loan(
                opportunity['token_in'],
                amount_wei,
                flash_loan_params
            )
            
            if not simulation['profitable']:
                return None
            
            result = await self.flash_loan.execute_arbitrage(
                opportunity['token_in'],
                amount_wei,
                self.get_router_address(opportunity['sell_dex']),
                self.min_profit_wei,
                Web3.to_bytes(text=f"{opportunity['buy_dex']},{opportunity['sell_dex']}")
            )
            
            return result
            
        except Exception as e:
            await self.discord.send_error_alert(f"DEX arbitrage failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_router_address(self, dex: str) -> str:
        routers = {
            'uniswap_v2': '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
            'uniswap_v3': self.config.DEX_ADDRESSES['uniswap_v3_router'],
            'sushiswap': self.config.DEX_ADDRESSES['sushiswap_router']
        }
        return routers.get(dex, routers['uniswap_v2'])
    
    async def cleanup(self):
        pass
    async def find_opportunity(self):
        """Find arbitrage opportunity"""
        try:
            return await self.scan_opportunities() if hasattr(self, 'scan_opportunities') else None
        except:
            return None

    async def find_opportunity(self):
        """Find arbitrage opportunity"""
        try:
            return await self.scan_opportunities() if hasattr(self, 'scan_opportunities') else None
        except:
            return None
