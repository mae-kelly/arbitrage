#!/usr/bin/env python3
import json
import urllib.request
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import ssl

# Disable SSL verification for some exchanges
ssl._create_default_https_context = ssl._create_unverified_context

class UltimateArbitrage:
    """MONITORS EVERY CRYPTO EXCHANGE IN EXISTENCE"""
    
    def __init__(self):
        self.prices = {}
        self.lock = threading.RLock()
        self.opportunities = 0
        self.profit = 0.0
        self.scans = 0
        self.executor = ThreadPoolExecutor(max_workers=50)
        
        # EVERY MAJOR EXCHANGE API
        self.exchanges = {
            # TIER 1 - Highest Volume
            'Binance': {
                'url': 'https://api.binance.com/api/v3/ticker/bookTicker?symbol=BTCUSDT',
                'parser': lambda d: {'bid': float(d['bidPrice']), 'ask': float(d['askPrice'])},
                'fee': 0.075
            },
            'Coinbase': {
                'url': 'https://api.coinbase.com/v2/exchange-rates?currency=BTC',
                'parser': lambda d: {'bid': float(d['data']['rates']['USD']) - 10, 'ask': float(d['data']['rates']['USD']) + 10},
                'fee': 0.25
            },
            'Kraken': {
                'url': 'https://api.kraken.com/0/public/Ticker?pair=XBTUSD',
                'parser': lambda d: {'bid': float(d['result']['XXBTZUSD']['b'][0]), 'ask': float(d['result']['XXBTZUSD']['a'][0])},
                'fee': 0.16
            },
            'OKX': {
                'url': 'https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT',
                'parser': lambda d: {'bid': float(d['data'][0]['bidPx']), 'ask': float(d['data'][0]['askPx'])} if d.get('data') else None,
                'fee': 0.08
            },
            'Bybit': {
                'url': 'https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT',
                'parser': lambda d: {'bid': float(d['result']['list'][0]['bid1Price']), 'ask': float(d['result']['list'][0]['ask1Price'])} if d.get('result') else None,
                'fee': 0.075
            },
            'Bitfinex': {
                'url': 'https://api-pub.bitfinex.com/v2/ticker/tBTCUSD',
                'parser': lambda d: {'bid': float(d[0]), 'ask': float(d[2])} if isinstance(d, list) else None,
                'fee': 0.10
            },
            
            # TIER 2 - Medium Volume
            'Bitstamp': {
                'url': 'https://www.bitstamp.net/api/v2/ticker/btcusd/',
                'parser': lambda d: {'bid': float(d['bid']), 'ask': float(d['ask'])},
                'fee': 0.25
            },
            'Gemini': {
                'url': 'https://api.gemini.com/v1/pubticker/btcusd',
                'parser': lambda d: {'bid': float(d['bid']), 'ask': float(d['ask'])},
                'fee': 0.35
            },
            'KuCoin': {
                'url': 'https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=BTC-USDT',
                'parser': lambda d: {'bid': float(d['data']['bestBid']), 'ask': float(d['data']['bestAsk'])} if d.get('data') else None,
                'fee': 0.10
            },
            'Gate.io': {
                'url': 'https://api.gateio.ws/api/v4/spot/tickers?currency_pair=BTC_USDT',
                'parser': lambda d: {'bid': float(d[0]['highest_bid']), 'ask': float(d[0]['lowest_ask'])} if d else None,
                'fee': 0.15
            },
            'Huobi': {
                'url': 'https://api.huobi.pro/market/detail/merged?symbol=btcusdt',
                'parser': lambda d: {'bid': float(d['tick']['bid'][0]), 'ask': float(d['tick']['ask'][0])} if d.get('tick') else None,
                'fee': 0.20
            },
            'Crypto.com': {
                'url': 'https://api.crypto.com/v2/public/get-ticker?instrument_name=BTC_USDT',
                'parser': lambda d: {'bid': float(d['result']['data']['b']), 'ask': float(d['result']['data']['k'])} if d.get('result') else None,
                'fee': 0.075
            },
            
            # TIER 3 - Regional/Specialty
            'Bittrex': {
                'url': 'https://api.bittrex.com/v3/markets/BTC-USDT/ticker',
                'parser': lambda d: {'bid': float(d['bidRate']), 'ask': float(d['askRate'])} if d else None,
                'fee': 0.25
            },
            'Poloniex': {
                'url': 'https://api.poloniex.com/markets/BTC_USDT/price',
                'parser': lambda d: {'bid': float(d['bid']), 'ask': float(d['ask'])} if d else None,
                'fee': 0.15
            },
            'BitMEX': {
                'url': 'https://www.bitmex.com/api/v1/orderBook/L2?symbol=XBTUSD&depth=1',
                'parser': lambda d: {'bid': d[1]['price'], 'ask': d[0]['price']} if len(d) >= 2 else None,
                'fee': 0.075
            },
            'Bitget': {
                'url': 'https://api.bitget.com/api/spot/v1/market/ticker?symbol=BTCUSDT_SPBL',
                'parser': lambda d: {'bid': float(d['data']['bestBid']), 'ask': float(d['data']['bestAsk'])} if d.get('data') else None,
                'fee': 0.10
            },
            'MEXC': {
                'url': 'https://api.mexc.com/api/v3/ticker/bookTicker?symbol=BTCUSDT',
                'parser': lambda d: {'bid': float(d['bidPrice']), 'ask': float(d['askPrice'])} if d else None,
                'fee': 0.10
            },
            'LBank': {
                'url': 'https://api.lbkex.com/v2/ticker/24hr.do?symbol=btc_usdt',
                'parser': lambda d: {'bid': float(d['data'][0]['ticker']['buy']), 'ask': float(d['data'][0]['ticker']['sell'])} if d.get('data') else None,
                'fee': 0.10
            },
            
            # DEX Aggregators (for reference prices)
            '1inch': {
                'url': 'https://api.1inch.io/v5.0/1/quote?fromTokenAddress=0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee&toTokenAddress=0xdac17f958d2ee523a2206206994597c13d831ec7&amount=1000000000000000000',
                'parser': lambda d: {'bid': float(d.get('toTokenAmount', 0))/1e6 - 20, 'ask': float(d.get('toTokenAmount', 0))/1e6 + 20} if d else None,
                'fee': 0.30
            },
        }
        
        self.active_exchanges = {}
        
    def fetch_price(self, name, config):
        """Fetch price from any exchange"""
        try:
            req = urllib.request.Request(config['url'], headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=0.5) as response:
                data = json.loads(response.read())
                parsed = config['parser'](data)
                
                if parsed and parsed['bid'] > 0 and parsed['ask'] > 0:
                    with self.lock:
                        self.prices[name] = {
                            'bid': parsed['bid'],
                            'ask': parsed['ask'],
                            'fee': config['fee'],
                            'ts': time.time()
                        }
                        self.active_exchanges[name] = True
                    return True
        except:
            with self.lock:
                self.active_exchanges[name] = False
        return False
    
    def find_opportunities(self):
        """Find profitable arbitrage across ALL exchanges"""
        opportunities = []
        
        with self.lock:
            active = [ex for ex, active in self.active_exchanges.items() if active]
            
            for buy_ex in active:
                for sell_ex in active:
                    if buy_ex != sell_ex:
                        buy_data = self.prices.get(buy_ex)
                        sell_data = self.prices.get(sell_ex)
                        
                        if buy_data and sell_data:
                            buy_price = buy_data['ask']
                            sell_price = sell_data['bid']
                            
                            if sell_price > buy_price:
                                spread = ((sell_price - buy_price) / buy_price) * 100
                                total_fee = buy_data['fee'] + sell_data['fee']
                                profit = spread - total_fee
                                
                                if profit > 0.01:  # Minimum 0.01% profit
                                    opportunities.append({
                                        'buy': buy_ex,
                                        'sell': sell_ex,
                                        'buy_price': buy_price,
                                        'sell_price': sell_price,
                                        'spread': spread,
                                        'fee': total_fee,
                                        'profit': profit,
                                        'profit_usd': profit * 100  # On $10k
                                    })
        
        return sorted(opportunities, key=lambda x: x['profit'], reverse=True)
    
    def scanner_loop(self):
        """Main scanning loop"""
        last_display = time.time()
        
        while True:
            # Fetch all prices in parallel
            futures = []
            for name, config in self.exchanges.items():
                future = self.executor.submit(self.fetch_price, name, config)
                futures.append(future)
            
            # Find opportunities
            opportunities = self.find_opportunities()
            self.scans += 1
            
            # Display updates
            if time.time() - last_display >= 1.0:
                last_display = time.time()
                
                active_count = len([e for e, a in self.active_exchanges.items() if a])
                
                print(f"\r📊 Monitoring {active_count}/{len(self.exchanges)} exchanges | "
                      f"🔍 {self.scans} scans | "
                      f"💰 {self.opportunities} opportunities found | "
                      f"💵 ${self.profit:.2f} profit", end='', flush=True)
                
                # Show best opportunity
                if opportunities and opportunities[0]['profit'] > 0.05:
                    opp = opportunities[0]
                    self.opportunities += 1
                    self.profit += opp['profit_usd']
                    
                    print(f"\n\n🎯 ARBITRAGE OPPORTUNITY #{self.opportunities}")
                    print(f"  BUY:  {opp['buy']:15} @ ${opp['buy_price']:,.2f}")
                    print(f"  SELL: {opp['sell']:15} @ ${opp['sell_price']:,.2f}")
                    print(f"  SPREAD: {opp['spread']:.3f}% | FEES: {opp['fee']:.3f}%")
                    print(f"  NET PROFIT: {opp['profit']:.3f}% (${opp['profit_usd']:.2f} on $10k)")
                    print(f"  💰 SESSION TOTAL: ${self.profit:.2f}\n", flush=True)
            
            time.sleep(0.1)  # Scan every 100ms
    
    def run(self):
        print("\n" + "="*70)
        print("    🌍 ULTIMATE GLOBAL EXCHANGE ARBITRAGE SCANNER")
        print(f"    Monitoring {len(self.exchanges)} exchanges worldwide")
        print("="*70)
        print("\nConnecting to all exchanges...\n")
        
        try:
            self.scanner_loop()
        except KeyboardInterrupt:
            print(f"\n\n📊 FINAL STATS:")
            print(f"  Exchanges monitored: {len(self.active_exchanges)}")
            print(f"  Total scans: {self.scans}")
            print(f"  Opportunities found: {self.opportunities}")
            print(f"  Total profit potential: ${self.profit:.2f}")

if __name__ == "__main__":
    bot = UltimateArbitrage()
    bot.run()
