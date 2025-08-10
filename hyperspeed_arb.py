#!/usr/bin/env python3
import json
import urllib.request
import time
import threading
import queue
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import sys
import os

# Optimize Python for speed
import gc
gc.disable()  # Disable garbage collection for speed

class HyperSpeedArbitrage:
    """PURE PYTHON MAXIMUM SPEED ARBITRAGE"""
    
    def __init__(self):
        self.prices = {}
        self.lock = threading.RLock()
        self.opportunities = 0
        self.profit = 0.0
        self.scans = 0
        self.start = time.perf_counter()
        
        # Use all CPU cores
        self.cpu_count = mp.cpu_count()
        self.executor = ThreadPoolExecutor(max_workers=self.cpu_count * 4)
        
        # Pre-compile request headers
        self.headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        
        # Exchanges with fastest APIs
        self.apis = {
            'Binance': ('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT', self.parse_binance),
            'Coinbase': ('https://api.coinbase.com/v2/exchange-rates?currency=BTC', self.parse_coinbase),
            'Kraken': ('https://api.kraken.com/0/public/Ticker?pair=XBTUSD', self.parse_kraken),
            'Bitstamp': ('https://www.bitstamp.net/api/v2/ticker/btcusd/', self.parse_bitstamp),
            'Gemini': ('https://api.gemini.com/v1/pubticker/btcusd', self.parse_gemini),
        }
        
        # Price queue for ultra-fast processing
        self.price_queue = queue.Queue(maxsize=1000)
        
    def parse_binance(self, data):
        return float(data['price'])
    
    def parse_coinbase(self, data):
        return float(data['data']['rates']['USD'])
    
    def parse_kraken(self, data):
        return float(data['result']['XXBTZUSD']['c'][0])
    
    def parse_bitstamp(self, data):
        return float(data['last'])
    
    def parse_gemini(self, data):
        return float(data['last'])
    
    def fetch_price(self, name, url, parser):
        """Ultra-fast price fetching"""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=0.5) as response:
                data = json.loads(response.read())
                price = parser(data)
                
                with self.lock:
                    self.prices[name] = {
                        'bid': price - 5,
                        'ask': price + 5,
                        'mid': price,
                        'ts': time.perf_counter_ns()
                    }
                
                # Queue for processing
                self.price_queue.put((name, price))
                return True
        except:
            return False
    
    def continuous_fetcher(self, name, url, parser):
        """Continuous price fetching thread"""
        while True:
            self.fetch_price(name, url, parser)
            # No sleep - maximum speed!
    
    def calculate_arbitrage(self):
        """Lightning-fast arbitrage calculation"""
        opps = []
        
        with self.lock:
            if len(self.prices) < 2:
                return opps
            
            exchanges = list(self.prices.keys())
            
            # Remove stale prices (older than 1 second)
            current = time.perf_counter_ns()
            for ex in list(self.prices.keys()):
                if current - self.prices[ex]['ts'] > 1_000_000_000:  # 1 second in nanoseconds
                    del self.prices[ex]
            
            # Fast nested loop for all pairs
            for i, ex1 in enumerate(exchanges):
                for ex2 in exchanges[i+1:]:
                    p1 = self.prices.get(ex1)
                    p2 = self.prices.get(ex2)
                    
                    if p1 and p2:
                        # Check both directions simultaneously
                        spread1 = (p2['bid'] - p1['ask']) / p1['ask'] * 100
                        spread2 = (p1['bid'] - p2['ask']) / p2['ask'] * 100
                        
                        if spread1 > 0.2:  # After fees
                            opps.append({
                                'buy': ex1, 'sell': ex2,
                                'profit': spread1 - 0.2,
                                'buy_p': p1['ask'],
                                'sell_p': p2['bid']
                            })
                        
                        if spread2 > 0.2:
                            opps.append({
                                'buy': ex2, 'sell': ex1,
                                'profit': spread2 - 0.2,
                                'buy_p': p2['ask'],
                                'sell_p': p1['bid']
                            })
        
        return sorted(opps, key=lambda x: x['profit'], reverse=True)
    
    def scanner_thread(self):
        """Ultra high-speed scanning thread"""
        last_display = time.perf_counter()
        scan_batch = 0
        
        while True:
            # Batch fetch all prices in parallel
            futures = []
            for name, (url, parser) in self.apis.items():
                future = self.executor.submit(self.fetch_price, name, url, parser)
                futures.append(future)
            
            # Don't wait for results, keep scanning
            
            # Calculate arbitrage
            opps = self.calculate_arbitrage()
            
            self.scans += 1
            scan_batch += 1
            
            # Display updates
            now = time.perf_counter()
            if now - last_display >= 0.5:  # Update display every 0.5 seconds
                scan_rate = scan_batch / (now - last_display)
                scan_batch = 0
                last_display = now
                
                # Clear line and show stats
                print(f"\r⚡ {scan_rate:.0f} scans/sec | "
                      f"💰 {self.opportunities} opps found | "
                      f"📊 {len(self.prices)} exchanges | "
                      f"💵 ${self.profit:.2f} profit", end='', flush=True)
                
                # Show opportunities
                if opps and opps[0]['profit'] > 0.01:
                    opp = opps[0]
                    self.opportunities += 1
                    self.profit += opp['profit'] * 100
                    
                    print(f"\n\n🎯 OPPORTUNITY #{self.opportunities}!")
                    print(f"  BUY:  {opp['buy']:10} @ ${opp['buy_p']:,.2f}")
                    print(f"  SELL: {opp['sell']:10} @ ${opp['sell_p']:,.2f}")
                    print(f"  PROFIT: {opp['profit']:.3f}% (${opp['profit']*100:.2f} on $10k)")
                    print(f"  SESSION: ${self.profit:.2f}\n", flush=True)
    
    def run(self):
        print("\n" + "="*60)
        print("    ⚡ HYPERSPEED ARBITRAGE ENGINE ⚡")
        print(f"    Using {self.cpu_count} CPU cores")
        print("="*60)
        print("\nStarting maximum speed scanning...\n")
        
        # Start continuous fetchers for each exchange
        for name, (url, parser) in self.apis.items():
            thread = threading.Thread(target=self.continuous_fetcher, args=(name, url, parser))
            thread.daemon = True
            thread.start()
        
        # Start scanner
        try:
            self.scanner_thread()
        except KeyboardInterrupt:
            elapsed = time.perf_counter() - self.start
            print(f"\n\n📊 FINAL STATISTICS:")
            print(f"  Runtime: {elapsed:.1f} seconds")
            print(f"  Total Scans: {self.scans:,}")
            print(f"  Scan Rate: {self.scans/elapsed:.0f} per second")
            print(f"  Opportunities: {self.opportunities}")
            print(f"  Profit Potential: ${self.profit:.2f}")

if __name__ == "__main__":
    # Set high priority
    try:
        os.nice(-20)
    except:
        pass
    
    bot = HyperSpeedArbitrage()
    bot.run()
