#!/usr/bin/env python3
import json
import urllib.request
import urllib.error
import time
from datetime import datetime
import threading

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class SimpleArbitrageBot:
    def __init__(self):
        self.prices = {}
        self.opportunities_found = 0
        self.total_profit = 0.0
        
    def fetch_price(self, exchange_name, url, parser):
        """Fetch price from an exchange"""
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                data = json.loads(response.read().decode())
                price_info = parser(data)
                self.prices[exchange_name] = price_info
                return True
        except Exception as e:
            # Silently fail and remove from prices if exists
            if exchange_name in self.prices:
                del self.prices[exchange_name]
            return False
    
    def parse_binance(self, data):
        price = float(data['price'])
        return {
            'bid': price - 5,
            'ask': price + 5,
            'mid': price
        }
    
    def parse_coinbase(self, data):
        price = float(data['data']['rates']['USD'])
        return {
            'bid': price - 8,
            'ask': price + 8,
            'mid': price
        }
    
    def parse_kraken(self, data):
        result = data['result']['XXBTZUSD']
        bid = float(result['b'][0])
        ask = float(result['a'][0])
        return {
            'bid': bid,
            'ask': ask,
            'mid': (bid + ask) / 2
        }
    
    def fetch_all_prices(self):
        """Fetch prices from all exchanges in parallel"""
        threads = []
        
        exchanges = [
            ('Binance', 'https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT', self.parse_binance),
            ('Coinbase', 'https://api.coinbase.com/v2/exchange-rates?currency=BTC', self.parse_coinbase),
            ('Kraken', 'https://api.kraken.com/0/public/Ticker?pair=XBTUSD', self.parse_kraken),
        ]
        
        for name, url, parser in exchanges:
            thread = threading.Thread(target=self.fetch_price, args=(name, url, parser))
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join(timeout=3)
        
        return len(self.prices)
    
    def find_opportunities(self):
        """Find arbitrage opportunities"""
        opportunities = []
        exchanges = list(self.prices.keys())
        
        for i in range(len(exchanges)):
            for j in range(i + 1, len(exchanges)):
                ex1, ex2 = exchanges[i], exchanges[j]
                
                # Buy from ex1, sell to ex2
                buy_price = self.prices[ex1]['ask']
                sell_price = self.prices[ex2]['bid']
                
                if sell_price > buy_price:
                    spread_pct = ((sell_price - buy_price) / buy_price) * 100
                    fee_pct = 0.2  # 0.1% each side
                    net_profit = spread_pct - fee_pct
                    
                    if net_profit > 0.01:  # 0.01% minimum
                        opportunities.append({
                            'buy': ex1,
                            'sell': ex2,
                            'buy_price': buy_price,
                            'sell_price': sell_price,
                            'profit_pct': net_profit,
                            'profit_usd': net_profit * 100  # on $10k
                        })
                
                # Buy from ex2, sell to ex1
                buy_price = self.prices[ex2]['ask']
                sell_price = self.prices[ex1]['bid']
                
                if sell_price > buy_price:
                    spread_pct = ((sell_price - buy_price) / buy_price) * 100
                    fee_pct = 0.2
                    net_profit = spread_pct - fee_pct
                    
                    if net_profit > 0.01:
                        opportunities.append({
                            'buy': ex2,
                            'sell': ex1,
                            'buy_price': buy_price,
                            'sell_price': sell_price,
                            'profit_pct': net_profit,
                            'profit_usd': net_profit * 100
                        })
        
        return sorted(opportunities, key=lambda x: x['profit_pct'], reverse=True)
    
    def run(self):
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}     MULTI-EXCHANGE ARBITRAGE BOT v3.0{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}\n")
        
        print(f"{Colors.GREEN}🚀 Starting arbitrage scanner...{Colors.RESET}")
        print(f"{Colors.YELLOW}📡 Connecting to exchanges...{Colors.RESET}\n")
        
        while True:
            try:
                # Fetch prices
                count = self.fetch_all_prices()
                
                if count >= 2:
                    # Show current prices
                    print(f"\n{Colors.BLUE}📊 [{datetime.now().strftime('%H:%M:%S')}] Current Prices:{Colors.RESET}")
                    for exchange, data in self.prices.items():
                        print(f"  {Colors.YELLOW}{exchange:10}{Colors.RESET} "
                              f"Bid: ${data['bid']:,.2f} | "
                              f"Ask: ${data['ask']:,.2f} | "
                              f"Spread: ${data['ask']-data['bid']:.2f}")
                    
                    # Find opportunities
                    opportunities = self.find_opportunities()
                    
                    if opportunities:
                        for opp in opportunities[:3]:  # Show top 3
                            self.opportunities_found += 1
                            self.total_profit += opp['profit_usd']
                            
                            print(f"\n{Colors.GREEN}{Colors.BOLD}🎯 OPPORTUNITY #{self.opportunities_found} DETECTED!{Colors.RESET}")
                            print(f"  {Colors.CYAN}BUY:  {opp['buy']:10} @ ${opp['buy_price']:,.2f}{Colors.RESET}")
                            print(f"  {Colors.GREEN}SELL: {opp['sell']:10} @ ${opp['sell_price']:,.2f}{Colors.RESET}")
                            print(f"  {Colors.YELLOW}PROFIT: {opp['profit_pct']:.3f}% (${opp['profit_usd']:.2f} on $10k){Colors.RESET}")
                            print(f"  {Colors.MAGENTA}SESSION TOTAL: ${self.total_profit:.2f}{Colors.RESET}")
                    else:
                        print(f"{Colors.RED}  ❌ No profitable opportunities (spreads < 0.21%){Colors.RESET}")
                else:
                    print(f"{Colors.RED}⚠️ Only {count} exchange(s) responding, need at least 2{Colors.RESET}")
                    if count == 1:
                        for ex, price in self.prices.items():
                            print(f"  Connected: {ex} - ${price['mid']:,.2f}")
                
                time.sleep(3)  # Check every 3 seconds
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"{Colors.RED}Error: {e}{Colors.RESET}")
                time.sleep(3)
        
        print(f"\n{Colors.YELLOW}Bot stopped.{Colors.RESET}")
        print(f"Total opportunities found: {self.opportunities_found}")
        print(f"Total theoretical profit: ${self.total_profit:.2f}")

if __name__ == "__main__":
    bot = SimpleArbitrageBot()
    try:
        bot.run()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Shutting down...{Colors.RESET}")
