# strategies/cex_dex_arbitrage.py

from typing import Dict, Optional
from web3 import Web3
from .base_strategy import BaseStrategy
from config import Config

class CEXDEXArbitrageStrategy(BaseStrategy):
    def __init__(self, okx_client, dex_client, discord_notifier):
        super().__init__("CEX-DEX Arbitrage")
        self.okx = okx_client
        self.dex = dex_client
        self.discord = discord_notifier
        self.config = Config()
        self.min_spread_percentage = 0.012
        self.execution_speed = 'fast'
        
    async def initialize(self):
        self.monitored_pairs = [
            ('ETH-USDT', self.config.TOKENS['WETH'], self.config.TOKENS['USDT']),
            ('ETH-USDC', self.config.TOKENS['WETH'], self.config.TOKENS['USDC'])
        ]
    
    async def execute(self) -> Optional[Dict]:
        if not self.should_execute():
            return None
        
        for cex_pair, dex_token_a, dex_token_b in self.monitored_pairs:
            opportunity = await self.find_arbitrage_opportunity(cex_pair, dex_token_a, dex_token_b)
            
            if opportunity:
                result = await self.execute_arbitrage(opportunity)
                if result:
                    self.update_metrics(result)
                    return result
        
        return None
    
    async def find_arbitrage_opportunity(self, cex_pair: str, dex_token_a: str, dex_token_b: str) -> Optional[Dict]:
        try:
            cex_ticker = await self.okx.get_ticker(cex_pair)
            
            dex_price = await self.dex.get_pool_price(dex_token_a, dex_token_b)
            
            if dex_price == 0:
                return None
            
            cex_bid = cex_ticker['bid']
            cex_ask = cex_ticker['ask']
            
            buy_cex_sell_dex_spread = (dex_price - cex_ask) / cex_ask
            buy_dex_sell_cex_spread = (cex_bid - dex_price) / dex_price
            
            if buy_cex_sell_dex_spread > self.min_spread_percentage:
                return {
                    'type': 'buy_cex_sell_dex',
                    'cex_pair': cex_pair,
                    'dex_token_a': dex_token_a,
                    'dex_token_b': dex_token_b,
                    'cex_price': cex_ask,
                    'dex_price': dex_price,
                    'spread': buy_cex_sell_dex_spread,
                    'estimated_profit': self.calculate_profit(1, cex_ask, dex_price, 'buy_cex')
                }
            
            elif buy_dex_sell_cex_spread > self.min_spread_percentage:
                return {
                    'type': 'buy_dex_sell_cex',
                    'cex_pair': cex_pair,
                    'dex_token_a': dex_token_a,
                    'dex_token_b': dex_token_b,
                    'cex_price': cex_bid,
                    'dex_price': dex_price,
                    'spread': buy_dex_sell_cex_spread,
                    'estimated_profit': self.calculate_profit(1, cex_bid, dex_price, 'buy_dex')
                }
            
        except Exception as e:
            print(f"Error finding opportunity: {e}")
        
        return None
    
    def calculate_profit(self, amount: float, cex_price: float, dex_price: float, direction: str) -> float:
        cex_fee = amount * 0.001
        dex_fee = amount * 0.003
        gas_cost_eth = 0.01
        gas_cost_usd = gas_cost_eth * 2000
        
        if direction == 'buy_cex':
            cost = amount * cex_price * (1 + 0.001)
            revenue = amount * dex_price * (1 - 0.003)
        else:
            cost = amount * dex_price * (1 + 0.003)
            revenue = amount * cex_price * (1 - 0.001)
        
        return revenue - cost - gas_cost_usd
    
    async def execute_arbitrage(self, opportunity: Dict) -> Dict:
        try:
            amount = min(1.0, self.config.MAX_POSITION_SIZE_ETH)
            
            if opportunity['estimated_profit'] < self.config.MIN_PROFIT_USD:
                return None
            
            if opportunity['type'] == 'buy_cex_sell_dex':
                cex_order_id = await self.okx.place_order(
                    opportunity['cex_pair'],
                    'buy',
                    amount
                )
                
                await self.wait_for_cex_fill(opportunity['cex_pair'], cex_order_id)
                
                amount_wei = Web3.to_wei(amount, 'ether')
                min_output = int(amount_wei * opportunity['dex_price'] * (1 - self.config.SLIPPAGE_TOLERANCE))
                
                dex_tx = await self.dex.swap_exact_input_single(
                    opportunity['dex_token_a'],
                    opportunity['dex_token_b'],
                    amount_wei,
                    min_output
                )
                
                actual_profit = await self.calculate_actual_profit(opportunity, amount)
                
                return {
                    'success': True,
                    'type': 'CEX-DEX Arbitrage',
                    'direction': opportunity['type'],
                    'amount': amount,
                    'profit': actual_profit,
                    'cex_order': cex_order_id,
                    'dex_tx': dex_tx
                }
                
            else:
                amount_wei = Web3.to_wei(amount, 'ether')
                min_output = int(amount_wei / opportunity['dex_price'] * (1 - self.config.SLIPPAGE_TOLERANCE))
                
                dex_tx = await self.dex.swap_exact_input_single(
                    opportunity['dex_token_b'],
                    opportunity['dex_token_a'],
                    int(amount * opportunity['dex_price'] * 10**6),
                    min_output
                )
                
                cex_order_id = await self.okx.place_order(
                    opportunity['cex_pair'],
                    'sell',
                    amount
                )
                
                await self.wait_for_cex_fill(opportunity['cex_pair'], cex_order_id)
                
                actual_profit = await self.calculate_actual_profit(opportunity, amount)
                
                return {
                    'success': True,
                    'type': 'CEX-DEX Arbitrage',
                    'direction': opportunity['type'],
                    'amount': amount,
                    'profit': actual_profit,
                    'cex_order': cex_order_id,
                    'dex_tx': dex_tx
                }
                
        except Exception as e:
            await self.discord.send_error_alert(f"Arbitrage execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def wait_for_cex_fill(self, pair: str, order_id: str, timeout: int = 30):
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = await self.okx.get_order_status(pair, order_id)
            
            if status['status'] in ['filled', 'partially_filled']:
                return status
            
            await asyncio.sleep(0.5)
        
        await self.okx.cancel_order(pair, order_id)
        raise TimeoutError(f"CEX order {order_id} not filled within {timeout} seconds")
    
    async def calculate_actual_profit(self, opportunity: Dict, amount: float) -> float:
        return opportunity['estimated_profit'] * amount
    
    async def cleanup(self):
        pass