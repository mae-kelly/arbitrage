import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from web3 import Web3
import ccxt.async_support as ccxt
import numpy as np

@dataclass
class ArbitrageOpportunity:
    source_exchange: str
    target_exchange: str
    token_pair: str
    buy_price: float
    sell_price: float
    profit_percentage: float
    volume: float
    gas_cost: float
    net_profit: float

class ArbitrageEngine:
    def __init__(self, config: Dict):
        self.config = config
        self.exchanges = {}
        self.web3_connections = {}
        self.min_profit_threshold = config.get('min_profit_percentage', 0.5)
        self.max_position_size = config.get('max_position_size', 1000)
        self.active_positions = {}
        
    async def initialize_exchanges(self):
        exchange_configs = self.config.get('exchanges', {})
        for exchange_name, config in exchange_configs.items():
            exchange_class = getattr(ccxt, exchange_name)
            self.exchanges[exchange_name] = exchange_class({
                'apiKey': config['api_key'],
                'secret': config['secret'],
                'sandbox': config.get('sandbox', True),
                'enableRateLimit': True,
            })
    
    async def scan_arbitrage_opportunities(self) -> List[ArbitrageOpportunity]:
        opportunities = []
        
        for token_pair in self.config.get('monitored_pairs', []):
            prices = await self.fetch_prices_across_exchanges(token_pair)
            
            if len(prices) < 2:
                continue
                
            sorted_prices = sorted(prices.items(), key=lambda x: x[1]['bid'])
            
            for i in range(len(sorted_prices)):
                for j in range(i + 1, len(sorted_prices)):
                    source_exchange, source_data = sorted_prices[i]
                    target_exchange, target_data = sorted_prices[j]
                    
                    profit_percentage = ((target_data['ask'] - source_data['bid']) / source_data['bid']) * 100
                    
                    if profit_percentage > self.min_profit_threshold:
                        gas_cost = await self.estimate_gas_cost(token_pair)
                        volume = min(source_data['volume'], target_data['volume'], self.max_position_size)
                        net_profit = (profit_percentage / 100) * volume - gas_cost
                        
                        if net_profit > 0:
                            opportunities.append(ArbitrageOpportunity(
                                source_exchange=source_exchange,
                                target_exchange=target_exchange,
                                token_pair=token_pair,
                                buy_price=source_data['bid'],
                                sell_price=target_data['ask'],
                                profit_percentage=profit_percentage,
                                volume=volume,
                                gas_cost=gas_cost,
                                net_profit=net_profit
                            ))
        
        return sorted(opportunities, key=lambda x: x.net_profit, reverse=True)
    
    async def fetch_prices_across_exchanges(self, token_pair: str) -> Dict:
        prices = {}
        
        tasks = []
        for exchange_name, exchange in self.exchanges.items():
            tasks.append(self.fetch_exchange_price(exchange_name, exchange, token_pair))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if not isinstance(result, Exception) and result:
                exchange_name = list(self.exchanges.keys())[i]
                prices[exchange_name] = result
        
        return prices
    
    async def fetch_exchange_price(self, exchange_name: str, exchange, token_pair: str):
        try:
            ticker = await exchange.fetch_ticker(token_pair)
            orderbook = await exchange.fetch_order_book(token_pair, limit=10)
            
            return {
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume': ticker['baseVolume'],
                'orderbook_depth': len(orderbook['bids']) + len(orderbook['asks'])
            }
        except Exception as e:
            logging.error(f"Error fetching price from {exchange_name}: {e}")
            return None
    
    async def execute_arbitrage(self, opportunity: ArbitrageOpportunity) -> bool:
        try:
            if opportunity.token_pair in self.active_positions:
                return False
            
            self.active_positions[opportunity.token_pair] = opportunity
            
            source_exchange = self.exchanges[opportunity.source_exchange]
            target_exchange = self.exchanges[opportunity.target_exchange]
            
            buy_order = await source_exchange.create_market_buy_order(
                opportunity.token_pair, 
                opportunity.volume
            )
            
            if buy_order['status'] == 'closed':
                sell_order = await target_exchange.create_market_sell_order(
                    opportunity.token_pair,
                    opportunity.volume
                )
                
                if sell_order['status'] == 'closed':
                    logging.info(f"Arbitrage executed: {opportunity.net_profit} profit")
                    del self.active_positions[opportunity.token_pair]
                    return True
            
            del self.active_positions[opportunity.token_pair]
            return False
            
        except Exception as e:
            logging.error(f"Error executing arbitrage: {e}")
            if opportunity.token_pair in self.active_positions:
                del self.active_positions[opportunity.token_pair]
            return False
    
    async def estimate_gas_cost(self, token_pair: str) -> float:
        base_gas_cost = 250000
        gas_price_gwei = 50
        eth_price_usd = 2000
        
        gas_cost_eth = (base_gas_cost * gas_price_gwei) / 1e9
        gas_cost_usd = gas_cost_eth * eth_price_usd
        
        return gas_cost_usd
    
    async def cleanup(self):
        for exchange in self.exchanges.values():
            await exchange.close()
