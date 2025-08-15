#!/usr/bin/env python3
"""
Real-time market data collection for ML training
"""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime
import ccxt
import yfinance as yf
import sqlite3
import os

class MarketDataCollector:
    def __init__(self):
        self.exchanges = self._initialize_exchanges()
        self.symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT']
        
    def _initialize_exchanges(self):
        return {
            'binance': ccxt.binance({'enableRateLimit': True}),
            'coinbase': ccxt.coinbasepro({'enableRateLimit': True}),
            'kraken': ccxt.kraken({'enableRateLimit': True}),
        }
    
    async def collect_orderbook_data(self):
        """Collect order book data for slippage modeling"""
        data = []
        
        for exchange_name, exchange in self.exchanges.items():
            for symbol in self.symbols:
                try:
                    orderbook = exchange.fetch_order_book(symbol)
                    
                    # Calculate liquidity metrics
                    bid_liquidity = sum([price * size for price, size in orderbook['bids'][:10]])
                    ask_liquidity = sum([price * size for price, size in orderbook['asks'][:10]])
                    spread = orderbook['asks'][0][0] - orderbook['bids'][0][0]
                    
                    data.append({
                        'timestamp': datetime.now(),
                        'exchange': exchange_name,
                        'symbol': symbol,
                        'bid_price': orderbook['bids'][0][0],
                        'ask_price': orderbook['asks'][0][0],
                        'spread': spread,
                        'bid_liquidity': bid_liquidity,
                        'ask_liquidity': ask_liquidity,
                    })
                    
                except Exception as e:
                    print(f"Error fetching {symbol} from {exchange_name}: {e}")
        
        return pd.DataFrame(data)
    
    def save_to_database(self, df, table_name='market_data'):
        """Save data to SQLite database"""
        os.makedirs('training_data', exist_ok=True)
        
        with sqlite3.connect('training_data/market_data.db') as conn:
            df.to_sql(table_name, conn, if_exists='append', index=False)

async def main():
    collector = MarketDataCollector()
    
    print("📊 Starting market data collection...")
    
    while True:
        try:
            # Collect data
            orderbook_data = await collector.collect_orderbook_data()
            
            # Save to database
            collector.save_to_database(orderbook_data, 'orderbooks')
            
            print(f"✅ Collected {len(orderbook_data)} data points")
            
            # Wait 10 seconds
            await asyncio.sleep(10)
            
        except KeyboardInterrupt:
            print("📊 Data collection stopped")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
