#!/usr/bin/env python3
import json
import urllib.request
import time
from datetime import datetime
import threading
import queue
import sys

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class UltraFastArbitrageBot:
    def __init__(self):
        self.prices = {}
        self.price_lock = threading.Lock()
        self.opportunities_found = 0
        self.total_profit = 0.0
        self.scans_per_second = 0
        self.last_opportunity_time = None
        self.running = True
        
    def continuous_price_fetcher(self, exchange_name, url, parser):
        """Continuously fetch prices from an exchange"""
        while self.running:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=1) as response:
                    data = json.loads(response.read().decode())
                    price_info = parser(data)
                    with self.price_lock:
                        self.prices[exchange_name] = {
                            **price_info,
                            'timestamp': time.time()
                        }
            except:
                pass
            time.sleep(0.1)  # Fetch every 100ms
    
    def parse_binance(self, data):
        price = float(data['price'])
        return {'bid': price - 5, 'ask': price + 5, 'mid': price}
    
    def parse_coinbase(self, data):
        price = float(data['data']['rates']['USD'])
        return {'bid': price - 8, 'ask': price + 8, 'mid': price}
    
    def parse_kraken(self, data):
        result = data['result']['XXBTZUSD']
        bid = float(result['b'][0])
        ask = float(result['a'][0])
        return {'bid': bid, 'ask': ask, 'mid': (bid + ask) / 2}
    
    def parse_okx(self, data):
        if 'data' in data and len(data['data']) > 0:
            price = float(data['data'][0]['last'])
            return {'bid': price - 6, 'ask': price + 6, 'mid': price}
        return None
    
    def start_price_feeds(self):
        """Start all price feed threads"""
        exchanges = [
            ('Binance', 'https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT', self.parse_binance),
            ('Coinbase', 'https://api.coinbase.com/v2/exchange-rates?currency=BTC', self.parse_coinbase),
            ('Kraken', 'https://api.kraken.com/0/public/Ticker?pair=XBTUSD', self.parse_kraken),
            ('OKX', 'https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT', self.parse_okx),
        ]
        
        threads = []
        for name, url, parser in exchanges:
            thread = threading.Thread(target=self.continuous_price_fetcher, args=(name, url, parser))
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        return threads
    
    def find_arbitrage(self):
        """Ultra-fast arbitrage detection"""
        opportunities = []
        
        with self.price_lock:
            exchanges = list(self.prices.keys())
            
            # Remove stale prices (older than 2 seconds)
            current_time = time.time()
            for ex in list(self.prices.keys()):
                if current_time - self.prices[ex]['timestamp'] > 2:
                    del self.prices[ex]
            
            exchanges = list(self.prices.keys())
            
            for i in range(len(exchanges)):
                for j in range(i + 1, len(exchanges)):
                    ex1, ex2 = exchanges[i], exchanges[j]
                    
                    # Check both directions
                    for buy_ex, sell_ex in [(ex1, ex2), (ex2, ex1)]:
                        buy_price = self.prices[buy_ex]['ask']
                        sell_price = self.prices[sell_ex]['bid']
                        
                        if sell_price > buy_price:
                            spread_pct = ((sell_price - buy_price) / buy_price) * 100
                            fee_pct = 0.2  # Total fees
                            net_profit = spread_pct - fee_pct
                            
                            if net_profit > 0.001:  # Even tiny profits
                                opportunities.append({
                                    'buy': buy_ex,
                                    'sell': sell_ex,
                                    'buy_price': buy_price,
                                    'sell_price': sell_price,
                                    'profit_pct': net_profit,
                                    'profit_usd': net_profit * 100,
                                    'spread_pct': spread_pct
                                })
        
        return sorted(opportunities, key=lambda x: x['profit_pct'], reverse=True)
    
    def display_loop(self):
        """Separate thread for display updates"""
        last_display = time.time()
        scan_count = 0
        
        while self.running:
            current_time = time.time()
            scan_count += 1
            
            # Calculate scans per second
            if current_time - last_display >= 1.0:
                self.scans_per_second = scan_count
                scan_count = 0
                last_display = current_time
                
                # Display current prices
                print(f"\n{Colors.BLUE}📊 [{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] "
                      f"Scans/sec: {self.scans_per_second} | "
                      f"Opportunities: {self.opportunities_found}{Colors.RESET}")
                
                with self.price_lock:
                    for exchange, data in self.prices.items():
                        age = current_time - data['timestamp']
                        status = "✓" if age < 0.5 else "⚠" if age < 1 else "✗"
                        print(f"  {status} {Colors.YELLOW}{exchange:10}{Colors.RESET} "
                              f"Bid: ${data['bid']:,.2f} | Ask: ${data['ask']:,.2f} | "
                              f"Age: {age:.1f}s")
            
            # Check for opportunities
            opportunities = self.find_arbitrage()
            
            if opportunities:
                for opp in opportunities[:1]:  # Show best one
                    if opp['profit_pct'] > 0.01:  # Only show meaningful opportunities
                        self.opportunities_found += 1
                        self.total_profit += opp['profit_usd']
                        self.last_opportunity_time = current_time
                        
                        print(f"\n{Colors.GREEN}{Colors.BOLD}🎯 OPPORTUNITY #{self.opportunities_found} "
                              f"@ {datetime.now().strftime('%H:%M:%S.%f')[:-3]}!{Colors.RESET}")
                        print(f"  {Colors.CYAN}BUY:  {opp['buy']:10} @ ${opp['buy_price']:,.2f}{Colors.RESET}")
                        print(f"  {Colors.GREEN}SELL: {opp['sell']:10} @ ${opp['sell_price']:,.2f}{Colors.RESET}")
                        print(f"  {Colors.YELLOW}SPREAD: {opp['spread_pct']:.3f}% | "
                              f"NET: {opp['profit_pct']:.3f}% (${opp['profit_usd']:.2f}){Colors.RESET}")
                        print(f"  {Colors.MAGENTA}💰 SESSION: ${self.total_profit:.2f}{Colors.RESET}")
            
            time.sleep(0.05)  # Check 20 times per second
    
    def run(self):
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}     ULTRA-FAST ARBITRAGE BOT v4.0{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}     20+ Scans/Second | Sub-100ms Detection{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}\n")
        
        print(f"{Colors.GREEN}🚀 Initializing ultra-fast price feeds...{Colors.RESET}")
        print(f"{Colors.YELLOW}⚡ Starting continuous monitoring...{Colors.RESET}\n")
        
        # Start price feed threads
        self.start_price_feeds()
        
        # Give feeds time to connect
        time.sleep(2)
        
        try:
            # Run display loop
            self.display_loop()
        except KeyboardInterrupt:
            self.running = False
            print(f"\n{Colors.YELLOW}Shutting down...{Colors.RESET}")
            print(f"Total opportunities detected: {self.opportunities_found}")
            print(f"Total theoretical profit: ${self.total_profit:.2f}")
            if self.scans_per_second > 0:
                print(f"Average scan rate: {self.scans_per_second} scans/second")

if __name__ == "__main__":
    bot = UltraFastArbitrageBot()
    try:
        bot.run()
    except KeyboardInterrupt:
        print(f"\nStopped.")
