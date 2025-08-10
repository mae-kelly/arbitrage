#!/usr/bin/env python3
import asyncio
import aiohttp
import time
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)

class ArbitrageBot:
    def __init__(self):
        self.prices = {}
        self.opportunities_found = 0
        self.total_profit = 0.0
        self.min_profit_threshold = 0.01  # 0.01% minimum
        
    async def fetch_binance(self, session):
        try:
            url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
            async with session.get(url, timeout=2) as resp:
                data = await resp.json()
                price = float(data['price'])
                self.prices['Binance'] = {
                    'bid': price - 5,  # Simulated spread
                    'ask': price + 5,
                    'mid': price
                }
                return True
        except:
            return False
    
    async def fetch_coinbase(self, session):
        try:
            url = "https://api.coinbase.com/v2/exchange-rates?currency=BTC"
            async with session.get(url, timeout=2) as resp:
                data = await resp.json()
                price = float(data['data']['rates']['USD'])
                self.prices['Coinbase'] = {
                    'bid': price - 8,
                    'ask': price + 8,
                    'mid': price
                }
                return True
        except:
            return False
    
    async def fetch_kraken(self, session):
        try:
            url = "https://api.kraken.com/0/public/Ticker?pair=XBTUSD"
            async with session.get(url, timeout=2) as resp:
                data = await resp.json()
                bid = float(data['result']['XXBTZUSD']['b'][0])
                ask = float(data['result']['XXBTZUSD']['a'][0])
                self.prices['Kraken'] = {
                    'bid': bid,
                    'ask': ask,
                    'mid': (bid + ask) / 2
                }
                return True
        except:
            return False
    
    async def fetch_okx(self, session):
        try:
            url = "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT"
            async with session.get(url, timeout=2) as resp:
                data = await resp.json()
                price = float(data['data'][0]['last'])
                self.prices['OKX'] = {
                    'bid': price - 6,
                    'ask': price + 6,
                    'mid': price
                }
                return True
        except:
            return False
    
    async def fetch_all_prices(self):
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.fetch_binance(session),
                self.fetch_coinbase(session),
                self.fetch_kraken(session),
                self.fetch_okx(session)
            ]
            results = await asyncio.gather(*tasks)
            return sum(results)  # Return count of successful fetches
    
    def find_arbitrage(self):
        opportunities = []
        exchanges = list(self.prices.keys())
        
        for i, ex1 in enumerate(exchanges):
            for ex2 in exchanges[i+1:]:
                # Buy from ex1, sell to ex2
                buy_price = self.prices[ex1]['ask']
                sell_price = self.prices[ex2]['bid']
                
                if sell_price > buy_price:
                    spread_pct = ((sell_price - buy_price) / buy_price) * 100
                    fee_pct = 0.2  # 0.1% each side
                    net_profit = spread_pct - fee_pct
                    
                    if net_profit > self.min_profit_threshold:
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
                    
                    if net_profit > self.min_profit_threshold:
                        opportunities.append({
                            'buy': ex2,
                            'sell': ex1,
                            'buy_price': buy_price,
                            'sell_price': sell_price,
                            'profit_pct': net_profit,
                            'profit_usd': net_profit * 100
                        })
        
        return sorted(opportunities, key=lambda x: x['profit_pct'], reverse=True)
    
    async def run(self):
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}     MULTI-EXCHANGE ARBITRAGE BOT v3.0")
        print(f"{Fore.CYAN}{'='*60}\n")
        
        print(f"{Fore.GREEN}🚀 Starting arbitrage scanner...")
        print(f"{Fore.YELLOW}📡 Connecting to exchanges...\n")
        
        while True:
            # Fetch prices
            count = await self.fetch_all_prices()
            
            if count >= 2:  # Need at least 2 exchanges
                # Show current prices
                print(f"\n{Fore.BLUE}📊 [{datetime.now().strftime('%H:%M:%S')}] Current Prices:")
                for exchange, data in self.prices.items():
                    print(f"  {Fore.YELLOW}{exchange:10} "
                          f"{Fore.WHITE}Bid: ${data['bid']:,.2f} | "
                          f"Ask: ${data['ask']:,.2f} | "
                          f"Spread: ${data['ask']-data['bid']:.2f}")
                
                # Find opportunities
                opportunities = self.find_arbitrage()
                
                if opportunities:
                    for opp in opportunities[:3]:  # Show top 3
                        self.opportunities_found += 1
                        self.total_profit += opp['profit_usd']
                        
                        print(f"\n{Fore.GREEN}🎯 OPPORTUNITY #{self.opportunities_found} DETECTED!")
                        print(f"  {Fore.CYAN}BUY:  {opp['buy']:10} @ ${opp['buy_price']:,.2f}")
                        print(f"  {Fore.GREEN}SELL: {opp['sell']:10} @ ${opp['sell_price']:,.2f}")
                        print(f"  {Fore.YELLOW}PROFIT: {opp['profit_pct']:.3f}% (${opp['profit_usd']:.2f} on $10k)")
                        print(f"  {Fore.MAGENTA}SESSION TOTAL: ${self.total_profit:.2f}")
                else:
                    print(f"{Fore.RED}  ❌ No profitable opportunities (after fees)")
            else:
                print(f"{Fore.RED}⚠️ Only {count} exchange(s) responding, need at least 2")
            
            await asyncio.sleep(2)  # Check every 2 seconds

if __name__ == "__main__":
    bot = ArbitrageBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Bot stopped. Total opportunities found: {bot.opportunities_found}")
        print(f"Total theoretical profit: ${bot.total_profit:.2f}")
