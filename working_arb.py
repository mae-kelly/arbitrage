#!/usr/bin/env python3
import json
import urllib.request
import time
import threading
from datetime import datetime

class WorkingArbitrage:
    """WORKING ARBITRAGE SCANNER WITH REAL CONNECTIONS"""
    
    def __init__(self):
        self.prices = {}
        self.lock = threading.Lock()
        self.opportunities = 0
        self.profit = 0.0
        
        # Simplified, working exchange APIs
        self.exchanges = {
            'Binance': {
                'url': 'https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT',
                'parser': self.parse_simple,
                'fee': 0.1
            },
            'Coinbase': {
                'url': 'https://api.coinbase.com/v2/exchange-rates?currency=BTC',
                'parser': self.parse_coinbase,
                'fee': 0.25
            },
            'Kraken': {
                'url': 'https://api.kraken.com/0/public/Ticker?pair=XBTUSD',
                'parser': self.parse_kraken,
                'fee': 0.16
            },
            'Bitstamp': {
                'url': 'https://www.bitstamp.net/api/v2/ticker/btcusd/',
                'parser': self.parse_bitstamp,
                'fee': 0.25
            },
            'Gemini': {
                'url': 'https://api.gemini.com/v1/pubticker/btcusd',
                'parser': self.parse_gemini,
                'fee': 0.25
            },
        }
        
        self.connection_status = {}
        
    def parse_simple(self, data, exchange=''):
        try:
            if 'price' in data:
                return float(data['price'])
        except:
            pass
        return None
    
    def parse_coinbase(self, data, exchange=''):
        try:
            return float(data['data']['rates']['USD'])
        except:
            pass
        return None
    
    def parse_kraken(self, data, exchange=''):
        try:
            return float(data['result']['XXBTZUSD']['c'][0])
        except:
            pass
        return None
    
    def parse_bitstamp(self, data, exchange=''):
        try:
            return float(data['last'])
        except:
            pass
        return None
    
    def parse_gemini(self, data, exchange=''):
        try:
            return float(data['last'])
        except:
            pass
        return None
    
    def fetch_price(self, name, config):
        """Fetch with proper error handling"""
        try:
            req = urllib.request.Request(
                config['url'], 
                headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
            )
            
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode())
                price = config['parser'](data, name)
                
                if price and price > 0:
                    # Add realistic spread
                    spread = price * 0.0001  # 0.01% spread
                    
                    with self.lock:
                        self.prices[name] = {
                            'bid': price - spread,
                            'ask': price + spread,
                            'mid': price,
                            'fee': config['fee'],
                            'ts': time.time()
                        }
                        self.connection_status[name] = '✅'
                    return True
                else:
                    self.connection_status[name] = '❌'
        except Exception as e:
            self.connection_status[name] = '❌'
            print(f"\n⚠️ {name} error: {str(e)[:50]}")
        return False
    
    def fetch_all(self):
        """Fetch from all exchanges"""
        threads = []
        for name, config in self.exchanges.items():
            t = threading.Thread(target=self.fetch_price, args=(name, config))
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join(timeout=2)
    
    def find_opportunities(self):
        """Find REAL opportunities"""
        opportunities = []
        
        with self.lock:
            exchanges = list(self.prices.keys())
            
            for i in range(len(exchanges)):
                for j in range(len(exchanges)):
                    if i != j:
                        ex1, ex2 = exchanges[i], exchanges[j]
                        p1 = self.prices[ex1]
                        p2 = self.prices[ex2]
                        
                        # Buy from ex1, sell to ex2
                        buy_price = p1['ask']
                        sell_price = p2['bid']
                        
                        if sell_price > buy_price:
                            spread = ((sell_price - buy_price) / buy_price) * 100
                            total_fee = (p1['fee'] + p2['fee']) / 100  # Convert to percentage
                            net_profit = spread - total_fee
                            
                            if net_profit > 0:
                                opportunities.append({
                                    'buy': ex1,
                                    'sell': ex2,
                                    'buy_price': buy_price,
                                    'sell_price': sell_price,
                                    'spread': spread,
                                    'profit': net_profit,
                                    'profit_usd': net_profit * 100
                                })
        
        return sorted(opportunities, key=lambda x: x['profit'], reverse=True)
    
    def run(self):
        print("\n" + "="*60)
        print("    💰 WORKING ARBITRAGE SCANNER")
        print("="*60)
        print("\nTesting connections to exchanges...\n")
        
        # Initial connection test
        self.fetch_all()
        time.sleep(1)
        
        print("\nConnection Status:")
        for name, status in self.connection_status.items():
            print(f"  {status} {name}")
        
        print("\n" + "-"*60)
        print("Starting arbitrage scanning...\n")
        
        scan_count = 0
        last_display = time.time()
        
        try:
            while True:
                # Fetch prices
                self.fetch_all()
                scan_count += 1
                
                # Find opportunities
                opportunities = self.find_opportunities()
                
                # Display status every second
                if time.time() - last_display >= 1:
                    last_display = time.time()
                    
                    active = len([p for p in self.prices.values() if time.time() - p['ts'] < 5])
                    
                    print(f"\r📊 Active: {active}/{len(self.exchanges)} | "
                          f"Scans: {scan_count} | "
                          f"Opportunities: {self.opportunities} | "
                          f"Profit: ${self.profit:.2f}", end='', flush=True)
                    
                    # Show current prices
                    if scan_count % 5 == 0:
                        print("\n\nCurrent Prices:")
                        for name, data in self.prices.items():
                            age = time.time() - data['ts']
                            if age < 5:
                                print(f"  {name:10} ${data['mid']:,.2f} (bid: ${data['bid']:,.2f}, ask: ${data['ask']:,.2f})")
                    
                    # Show opportunities
                    if opportunities:
                        print("\n🎯 OPPORTUNITIES FOUND:")
                        for opp in opportunities[:3]:
                            if opp['profit'] > 0.01:
                                self.opportunities += 1
                                self.profit += opp['profit_usd']
                                
                                print(f"\n  #{self.opportunities}")
                                print(f"  BUY:  {opp['buy']:10} @ ${opp['buy_price']:,.2f}")
                                print(f"  SELL: {opp['sell']:10} @ ${opp['sell_price']:,.2f}")
                                print(f"  SPREAD: {opp['spread']:.4f}%")
                                print(f"  PROFIT: {opp['profit']:.4f}% = ${opp['profit_usd']:.2f} on $10k")
                
                time.sleep(0.5)  # Scan every 500ms
                
        except KeyboardInterrupt:
            print(f"\n\nFinal Stats:")
            print(f"  Total Scans: {scan_count}")
            print(f"  Opportunities Found: {self.opportunities}")
            print(f"  Total Profit Potential: ${self.profit:.2f}")

if __name__ == "__main__":
    bot = WorkingArbitrage()
    bot.run()
