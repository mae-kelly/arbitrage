import asyncio
import ccxt.pro as ccxtpro
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
import time

logger = logging.getLogger(__name__)

class BinanceIntegration:
    def __init__(self, api_key: str, secret: str, testnet: bool = False):
        self.api_key = api_key
        self.secret = secret
        self.testnet = testnet
        self.exchange = None
        self.is_connected = False
        self.orderbook_cache = {}
        self.balance_cache = {}
        
    async def initialize(self):
        logger.info("Initializing Binance integration")
        
        try:
            self.exchange = ccxtpro.binance({
                'apiKey': self.api_key,
                'secret': self.secret,
                'sandbox': self.testnet,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                }
            })
            
            await self.exchange.load_markets()
            self.is_connected = True
            
            logger.info("Binance integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Binance initialization error: {e}")
            raise
    
    async def start_real_time_feeds(self):
        if not self.is_connected:
            await self.initialize()
        
        logger.info("Starting Binance real-time feeds")
        
        major_symbols = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT',
            'DOT/USDT', 'DOGE/USDT', 'AVAX/USDT', 'LUNA/USDT', 'LINK/USDT'
        ]
        
        asyncio.create_task(self._orderbook_feed_loop(major_symbols))
        asyncio.create_task(self._ticker_feed_loop(major_symbols))
        asyncio.create_task(self._balance_update_loop())
    
    async def get_orderbook(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        try:
            if symbol in self.orderbook_cache:
                cached_book = self.orderbook_cache[symbol]
                if time.time() - cached_book['timestamp'] < 1:
                    return cached_book['data']
            
            orderbook = await self.exchange.fetch_order_book(symbol, limit)
            
            self.orderbook_cache[symbol] = {
                'data': orderbook,
                'timestamp': time.time()
            }
            
            return orderbook
            
        except Exception as e:
            logger.error(f"Error fetching orderbook for {symbol}: {e}")
            return None
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        try:
            return await self.exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None
    
    async def get_balance(self) -> Dict[str, Any]:
        try:
            if 'balance' in self.balance_cache:
                cached_balance = self.balance_cache['balance']
                if time.time() - cached_balance['timestamp'] < 5:
                    return cached_balance['data']
            
            balance = await self.exchange.fetch_balance()
            
            self.balance_cache['balance'] = {
                'data': balance,
                'timestamp': time.time()
            }
            
            return balance
            
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return None
    
    async def place_market_order(self, symbol: str, side: str, amount: float) -> Dict[str, Any]:
        try:
            order = await self.exchange.create_market_order(symbol, side, amount)
            logger.info(f"Market order placed: {symbol} {side} {amount}")
            return order
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            return None
    
    async def place_limit_order(self, symbol: str, side: str, amount: float, price: float) -> Dict[str, Any]:
        try:
            order = await self.exchange.create_limit_order(symbol, side, amount, price)
            logger.info(f"Limit order placed: {symbol} {side} {amount} @ {price}")
            return order
        except Exception as e:
            logger.error(f"Error placing limit order: {e}")
            return None
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        try:
            await self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def execute_arbitrage(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        try:
            symbol = f"{opportunity['token_in']}/{opportunity['token_out']}"
            amount = float(opportunity['amount'])
            
            current_price = await self.get_ticker(symbol)
            if not current_price:
                return {"success": False, "error": "Could not fetch price"}
            
            if opportunity['side'] == 'buy':
                order = await self.place_market_order(symbol, 'buy', amount)
            else:
                order = await self.place_market_order(symbol, 'sell', amount)
            
            if order:
                profit = float(opportunity.get('expected_profit', 0))
                return {
                    "success": True,
                    "order_id": order['id'],
                    "filled_amount": order.get('filled', 0),
                    "average_price": order.get('average', 0),
                    "profit": profit,
                    "fees": order.get('fee', {}).get('cost', 0)
                }
            else:
                return {"success": False, "error": "Order placement failed"}
                
        except Exception as e:
            logger.error(f"Arbitrage execution error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _orderbook_feed_loop(self, symbols: List[str]):
        while self.is_connected:
            try:
                for symbol in symbols:
                    orderbook = await self.exchange.watch_order_book(symbol)
                    self.orderbook_cache[symbol] = {
                        'data': orderbook,
                        'timestamp': time.time()
                    }
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Orderbook feed error: {e}")
                await asyncio.sleep(1)
    
    async def _ticker_feed_loop(self, symbols: List[str]):
        while self.is_connected:
            try:
                for symbol in symbols:
                    ticker = await self.exchange.watch_ticker(symbol)
                    # Process ticker updates for opportunity detection
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Ticker feed error: {e}")
                await asyncio.sleep(1)
    
    async def _balance_update_loop(self):
        while self.is_connected:
            try:
                balance = await self.exchange.fetch_balance()
                self.balance_cache['balance'] = {
                    'data': balance,
                    'timestamp': time.time()
                }
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Balance update error: {e}")
                await asyncio.sleep(30)
    
    async def close(self):
        if self.exchange:
            await self.exchange.close()
        self.is_connected = False
        logger.info("Binance connection closed")
