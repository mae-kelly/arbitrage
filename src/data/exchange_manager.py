"""Exchange API Manager for crypto arbitrage"""
import ccxt
import asyncio
from typing import Dict, List, Optional
from loguru import logger
from ..types import OrderBook, PriceLevel

class ExchangeManager:
    def __init__(self):
        self.exchanges = {}
        self.symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        
    def add_exchange(self, name: str, config: dict = None):
        """Add an exchange to the manager"""
        try:
            if name.lower() == 'binance':
                exchange = ccxt.binance(config or {})
            elif name.lower() == 'coinbase':
                exchange = ccxt.coinbase(config or {})
            elif name.lower() == 'kraken':
                exchange = ccxt.kraken(config or {})
            else:
                exchange = getattr(ccxt, name.lower())(config or {})
            
            self.exchanges[name] = exchange
            logger.info(f"Added exchange: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add exchange {name}: {e}")
            return False
    
    async def get_orderbook(self, exchange_name: str, symbol: str) -> Optional[OrderBook]:
        """Get orderbook for a symbol from an exchange"""
        try:
            if exchange_name not in self.exchanges:
                return None
                
            exchange = self.exchanges[exchange_name]
            orderbook_data = exchange.fetch_order_book(symbol)
            
            bids = [PriceLevel(price=bid[0], volume=bid[1]) for bid in orderbook_data['bids'][:5]]
            asks = [PriceLevel(price=ask[0], volume=ask[1]) for ask in orderbook_data['asks'][:5]]
            
            return OrderBook(
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=orderbook_data['timestamp'],
                exchange=exchange_name
            )
        except Exception as e:
            logger.error(f"Failed to get orderbook from {exchange_name}: {e}")
            return None
    
    def get_supported_symbols(self) -> List[str]:
        """Get list of supported trading symbols"""
        return self.symbols
