import asyncio
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
import time

logger = logging.getLogger(__name__)

class OpportunityAggregator:
    def __init__(self, price_aggregator, chain_manager):
        self.price_aggregator = price_aggregator
        self.chain_manager = chain_manager
        self.opportunity_cache = {}
        self.is_running = False
        
    async def initialize(self):
        logger.info("Initializing Opportunity Aggregator")
        logger.info("Opportunity Aggregator initialized")
    
    async def start(self):
        if self.is_running:
            return
            
        logger.info("Starting Opportunity Aggregator")
        self.is_running = True
        
        asyncio.create_task(self._opportunity_detection_loop())
        asyncio.create_task(self._cache_cleanup_loop())
        
        logger.info("Opportunity Aggregator started")
    
    async def stop(self):
        if not self.is_running:
            return
            
        logger.info("Stopping Opportunity Aggregator")
        self.is_running = False
        logger.info("Opportunity Aggregator stopped")
    
    async def get_opportunities(self) -> List[Dict[str, Any]]:
        opportunities = []
        
        try:
            dex_opportunities = await self._scan_dex_arbitrage()
            liquidation_opportunities = await self._scan_liquidations()
            bridge_opportunities = await self._scan_bridge_arbitrage()
            nft_opportunities = await self._scan_nft_arbitrage()
            
            opportunities.extend(dex_opportunities)
            opportunities.extend(liquidation_opportunities)
            opportunities.extend(bridge_opportunities)
            opportunities.extend(nft_opportunities)
            
            opportunities = self._filter_and_rank_opportunities(opportunities)
            
        except Exception as e:
            logger.error(f"Opportunity scanning error: {e}")
        
        return opportunities[:50]
    
    async def _opportunity_detection_loop(self):
        while self.is_running:
            try:
                opportunities = await self.get_opportunities()
                
                for opp in opportunities:
                    if opp["profit_potential"] > 0.01:
                        self.opportunity_cache[opp["id"]] = {
                            "opportunity": opp,
                            "timestamp": time.time()
                        }
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Opportunity detection error: {e}")
                await asyncio.sleep(2)
    
    async def _cache_cleanup_loop(self):
        while self.is_running:
            try:
                current_time = time.time()
                expired_keys = [
                    key for key, value in self.opportunity_cache.items()
                    if current_time - value["timestamp"] > 60
                ]
                
                for key in expired_keys:
                    del self.opportunity_cache[key]
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(60)
    
    async def _scan_dex_arbitrage(self) -> List[Dict[str, Any]]:
        opportunities = []
        
        try:
            token_pairs = [
                ("WETH", "USDC"), ("WETH", "USDT"), ("WETH", "DAI"),
                ("WBTC", "WETH"), ("USDC", "USDT"), ("DAI", "USDC")
            ]
            
            for token_in, token_out in token_pairs:
                price_differences = await self._calculate_price_differences(token_in, token_out)
                
                for diff in price_differences:
                    if diff["profit_percentage"] > 0.005:
                        opportunity = {
                            "id": f"dex_arb_{token_in}_{token_out}_{int(time.time())}",
                            "strategy": "dex_arbitrage",
                            "token_in": token_in,
                            "token_out": token_out,
                            "amount": diff["optimal_amount"],
                            "exchanges": [diff["buy_exchange"], diff["sell_exchange"]],
                            "profit_potential": diff["profit_percentage"],
                            "estimated_profit": diff["estimated_profit"],
                            "confidence": diff["confidence"],
                            "timestamp": time.time()
                        }
                        opportunities.append(opportunity)
            
        except Exception as e:
            logger.error(f"DEX arbitrage scanning error: {e}")
        
        return opportunities
    
    async def _scan_liquidations(self) -> List[Dict[str, Any]]:
        opportunities = []
        
        try:
            risky_positions = await self._get_risky_positions()
            
            for position in risky_positions:
                if position["health_factor"] < 1.1:
                    liquidation_bonus = await self._calculate_liquidation_bonus(position)
                    
                    if liquidation_bonus > 500:
                        opportunity = {
                            "id": f"liquidation_{position['user']}_{int(time.time())}",
                            "strategy": "liquidation_hunting",
                            "user": position["user"],
                            "collateral_token": position["collateral_token"],
                            "debt_token": position["debt_token"],
                            "collateral_amount": position["collateral_amount"],
                            "debt_amount": position["debt_amount"],
                            "health_factor": position["health_factor"],
                            "profit_potential": liquidation_bonus / position["collateral_value"],
                            "estimated_profit": liquidation_bonus,
                            "confidence": 0.9,
                            "timestamp": time.time()
                        }
                        opportunities.append(opportunity)
            
        except Exception as e:
            logger.error(f"Liquidation scanning error: {e}")
        
        return opportunities
    
    async def _scan_bridge_arbitrage(self) -> List[Dict[str, Any]]:
        opportunities = []
        
        try:
            chain_pairs = [(1, 137), (1, 56), (1, 42161), (137, 56)]
            
            for chain_a, chain_b in chain_pairs:
                price_differences = await self._scan_cross_chain_prices(chain_a, chain_b)
                
                for diff in price_differences:
                    if diff["profit_percentage"] > 0.008:
                        opportunity = {
                            "id": f"bridge_arb_{chain_a}_{chain_b}_{diff['token']}_{int(time.time())}",
                            "strategy": "bridge_arbitrage",
                            "token": diff["token"],
                            "chain_from": chain_a,
                            "chain_to": chain_b,
                            "amount": diff["optimal_amount"],
                            "profit_potential": diff["profit_percentage"],
                            "estimated_profit": diff["estimated_profit"],
                            "bridge_fee": diff["bridge_fee"],
                            "confidence": diff["confidence"],
                            "timestamp": time.time()
                        }
                        opportunities.append(opportunity)
            
        except Exception as e:
            logger.error(f"Bridge arbitrage scanning error: {e}")
        
        return opportunities
    
    async def _scan_nft_arbitrage(self) -> List[Dict[str, Any]]:
        opportunities = []
        
        try:
            popular_collections = [
                "0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d",
                "0x60e4d786628fea6478f785a6d7e704777c86a7c6",
                "0xba30e5f9bb24caa003e9f2f0497ad287fdf95623"
            ]
            
            for collection in popular_collections:
                price_differences = await self._scan_nft_marketplaces(collection)
                
                for diff in price_differences:
                    if diff["profit_eth"] > 0.1:
                        opportunity = {
                            "id": f"nft_arb_{collection}_{diff['token_id']}_{int(time.time())}",
                            "strategy": "nft_arbitrage",
                            "collection": collection,
                            "token_id": diff["token_id"],
                            "buy_marketplace": diff["buy_marketplace"],
                            "sell_marketplace": diff["sell_marketplace"],
                            "buy_price": diff["buy_price"],
                            "sell_price": diff["sell_price"],
                            "profit_potential": diff["profit_percentage"],
                            "estimated_profit": diff["profit_eth"],
                            "confidence": diff["confidence"],
                            "timestamp": time.time()
                        }
                        opportunities.append(opportunity)
            
        except Exception as e:
            logger.error(f"NFT arbitrage scanning error: {e}")
        
        return opportunities
    
    def _filter_and_rank_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered = [
            opp for opp in opportunities
            if opp["profit_potential"] > 0.005 and opp["confidence"] > 0.7
        ]
        
        return sorted(filtered, key=lambda x: x["profit_potential"] * x["confidence"], reverse=True)
    
    async def _calculate_price_differences(self, token_in: str, token_out: str) -> List[Dict[str, Any]]:
        return [
            {
                "buy_exchange": "uniswap_v3",
                "sell_exchange": "sushiswap",
                "profit_percentage": 0.008,
                "optimal_amount": Decimal("10000"),
                "estimated_profit": Decimal("80"),
                "confidence": 0.85
            }
        ]
    
    async def _get_risky_positions(self) -> List[Dict[str, Any]]:
        return [
            {
                "user": "0x1234567890123456789012345678901234567890",
                "collateral_token": "WETH",
                "debt_token": "USDC",
                "collateral_amount": Decimal("10"),
                "debt_amount": Decimal("15000"),
                "collateral_value": Decimal("20000"),
                "health_factor": 1.05
            }
        ]
    
    async def _calculate_liquidation_bonus(self, position: Dict[str, Any]) -> Decimal:
        return Decimal("1000")
    
    async def _scan_cross_chain_prices(self, chain_a: int, chain_b: int) -> List[Dict[str, Any]]:
        return [
            {
                "token": "USDC",
                "profit_percentage": 0.012,
                "optimal_amount": Decimal("50000"),
                "estimated_profit": Decimal("600"),
                "bridge_fee": Decimal("50"),
                "confidence": 0.8
            }
        ]
    
    async def _scan_nft_marketplaces(self, collection: str) -> List[Dict[str, Any]]:
        return [
            {
                "token_id": "1234",
                "buy_marketplace": "opensea",
                "sell_marketplace": "blur",
                "buy_price": Decimal("5.5"),
                "sell_price": Decimal("6.2"),
                "profit_percentage": 0.127,
                "profit_eth": Decimal("0.7"),
                "confidence": 0.75
            }
        ]
