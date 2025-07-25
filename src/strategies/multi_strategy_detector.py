"""Multi-strategy arbitrage detection engine"""
import asyncio
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass
import time
import numpy as np
from loguru import logger
import json

@dataclass
class OpportunitySignal:
    strategy_type: str
    confidence: float
    expected_profit: Decimal
    profit_percentage: Decimal
    execution_complexity: int
    time_sensitivity: int  # 1-10 scale
    required_capital: Decimal
    risk_score: float
    metadata: Dict

class MultiStrategyDetector:
    def __init__(self, exchange_manager, dex_manager):
        self.exchange_manager = exchange_manager
        self.dex_manager = dex_manager
        self.active_strategies = {
            'spatial': True,
            'triangular': True,
            'cross_chain': True,
            'funding_rate': True,
            'statistical': True,
            'mev': False,  # Disabled by default due to complexity
            'launch_arbitrage': True
        }
        
        self.min_profit_thresholds = {
            'spatial': Decimal('0.003'),      # 0.3%
            'triangular': Decimal('0.005'),   # 0.5%
            'cross_chain': Decimal('0.01'),   # 1.0%
            'funding_rate': Decimal('0.002'), # 0.2%
            'statistical': Decimal('0.004'),  # 0.4%
            'mev': Decimal('0.02'),          # 2.0%
            'launch_arbitrage': Decimal('0.05') # 5.0%
        }
        
        self.opportunities_cache = []
        self.historical_data = {}
    
    async def detect_all_opportunities(self, symbols: List[str]) -> List[OpportunitySignal]:
        """Run all active detection strategies in parallel"""
        all_tasks = []
        
        if self.active_strategies['spatial']:
            all_tasks.append(asyncio.create_task(self.detect_spatial_arbitrage(symbols)))
        
        if self.active_strategies['triangular']:
            all_tasks.append(asyncio.create_task(self.detect_triangular_arbitrage(symbols)))
        
        if self.active_strategies['cross_chain']:
            all_tasks.append(asyncio.create_task(self.detect_cross_chain_arbitrage()))
        
        if self.active_strategies['funding_rate']:
            all_tasks.append(asyncio.create_task(self.detect_funding_rate_arbitrage(symbols)))
        
        if self.active_strategies['statistical']:
            all_tasks.append(asyncio.create_task(self.detect_statistical_arbitrage(symbols)))
        
        if self.active_strategies['launch_arbitrage']:
            all_tasks.append(asyncio.create_task(self.detect_launch_arbitrage()))
        
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        all_opportunities = []
        for result in results:
            if isinstance(result, list):
                all_opportunities.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Strategy detection failed: {result}")
        
        # Score and filter opportunities
        high_quality_opportunities = self._score_and_filter_opportunities(all_opportunities)
        
        self.opportunities_cache = high_quality_opportunities
        return high_quality_opportunities
    
    async def detect_spatial_arbitrage(self, symbols: List[str]) -> List[OpportunitySignal]:
        """Enhanced spatial arbitrage detection across all exchanges"""
        opportunities = []
        
        for symbol in symbols:
            try:
                orderbooks = await self.exchange_manager.get_all_orderbooks(symbol)
                
                if len(orderbooks) < 2:
                    continue
                
                # Find best opportunities between all exchange pairs
                exchanges = list(orderbooks.keys())
                
                for i in range(len(exchanges)):
                    for j in range(i + 1, len(exchanges)):
                        buy_exchange = exchanges[i]
                        sell_exchange = exchanges[j]
                        
                        buy_ob = orderbooks[buy_exchange]
                        sell_ob = orderbooks[sell_exchange]
                        
                        if not buy_ob['asks'] or not sell_ob['bids']:
                            continue
                        
                        # Check both directions
                        opportunities.extend(await self._analyze_spatial_pair(
                            symbol, buy_exchange, sell_exchange, buy_ob, sell_ob
                        ))
                        
            except Exception as e:
                logger.error(f"Spatial arbitrage detection failed for {symbol}: {e}")
        
        return opportunities
    
    async def _analyze_spatial_pair(self, symbol: str, buy_exchange: str, sell_exchange: str, 
                                   buy_ob: Dict, sell_ob: Dict) -> List[OpportunitySignal]:
        """Analyze spatial arbitrage between two exchanges"""
        opportunities = []
        
        try:
            best_ask = Decimal(str(buy_ob['asks'][0][0]))
            best_bid = Decimal(str(sell_ob['bids'][0][0]))
            
            if best_bid > best_ask:
                # Calculate depth-adjusted profit
                available_volume = min(
                    Decimal(str(buy_ob['asks'][0][1])),
                    Decimal(str(sell_ob['bids'][0][1]))
                )
                
                profit_per_unit = best_bid - best_ask
                profit_percentage = profit_per_unit / best_ask
                
                if profit_percentage >= self.min_profit_thresholds['spatial']:
                    # Factor in exchange latencies
                    buy_latency = self.exchange_manager.latencies.get(buy_exchange, 100)
                    sell_latency = self.exchange_manager.latencies.get(sell_exchange, 100)
                    total_latency = buy_latency + sell_latency
                    
                    # Adjust confidence based on latency and volume
                    confidence = self._calculate_spatial_confidence(
                        profit_percentage, available_volume, total_latency, symbol
                    )
                    
                    if confidence > 0.6:  # Only high-confidence opportunities
                        opportunity = OpportunitySignal(
                            strategy_type='spatial',
                            confidence=confidence,
                            expected_profit=profit_per_unit * available_volume,
                            profit_percentage=profit_percentage,
                            execution_complexity=2,  # Simple buy/sell
                            time_sensitivity=8,       # High time sensitivity
                            required_capital=best_ask * available_volume,
                            risk_score=self._calculate_risk_score(buy_exchange, sell_exchange),
                            metadata={
                                'symbol': symbol,
                                'buy_exchange': buy_exchange,
                                'sell_exchange': sell_exchange,
                                'buy_price': best_ask,
                                'sell_price': best_bid,
                                'volume': available_volume,
                                'total_latency': total_latency
                            }
                        )
                        opportunities.append(opportunity)
            
        except Exception as e:
            logger.error(f"Error analyzing spatial pair {buy_exchange}-{sell_exchange}: {e}")
        
        return opportunities
    
    def _calculate_spatial_confidence(self, profit_pct: Decimal, volume: Decimal, 
                                    latency: float, symbol: str) -> float:
        """Calculate confidence score for spatial arbitrage"""
        base_confidence = 0.7
        
        # Profit factor (higher profit = higher confidence)
        profit_factor = min(float(profit_pct) * 100, 1.0)  # Cap at 1.0
        
        # Volume factor (more volume = higher confidence)
        volume_factor = min(float(volume) / 10.0, 1.0)  # Normalize to 10 units
        
        # Latency factor (lower latency = higher confidence)
        latency_factor = max(0.1, 1.0 - (latency / 1000.0))  # Normalize to 1 second
        
        # Symbol factor (major pairs = higher confidence)
        major_pairs = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        symbol_factor = 1.0 if symbol in major_pairs else 0.8
        
        confidence = base_confidence * profit_factor * volume_factor * latency_factor * symbol_factor
        return min(confidence, 1.0)
    
    async def detect_triangular_arbitrage(self, symbols: List[str]) -> List[OpportunitySignal]:
        """Detect triangular arbitrage within exchanges"""
        opportunities = []
        
        for exchange_id in self.exchange_manager.exchanges.keys():
            if not self.exchange_manager.connection_health.get(exchange_id, False):
                continue
            
            try:
                # Get orderbooks for major pairs
                orderbooks = {}
                for symbol in symbols:
                    try:
                        ob_data = await self.exchange_manager._fetch_orderbook_safe(exchange_id, symbol)
                        if ob_data and ob_data['bids'] and ob_data['asks']:
                            orderbooks[symbol] = ob_data
                    except Exception:
                        continue
                
                if len(orderbooks) < 3:
                    continue
                
                # Find triangular opportunities
                triangular_opps = await self._find_triangular_opportunities(exchange_id, orderbooks)
                opportunities.extend(triangular_opps)
                
            except Exception as e:
                logger.error(f"Triangular arbitrage detection failed for {exchange_id}: {e}")
        
        return opportunities
    
    async def _find_triangular_opportunities(self, exchange_id: str, orderbooks: Dict) -> List[OpportunitySignal]:
        """Find triangular arbitrage opportunities within an exchange"""
        opportunities = []
        
        # Define currency triangles to check
        triangles = [
            ('BTC/USDT', 'ETH/USDT', 'ETH/BTC'),
            ('BTC/USDT', 'BNB/USDT', 'BNB/BTC'),
            ('ETH/USDT', 'BNB/USDT', 'BNB/ETH'),
            ('BTC/USDT', 'ADA/USDT', 'ADA/BTC'),
            ('ETH/USDT', 'ADA/USDT', 'ADA/ETH')
        ]
        
        for pair1, pair2, pair3 in triangles:
            if all(pair in orderbooks for pair in [pair1, pair2, pair3]):
                try:
                    opp = await self._calculate_triangular_profit(
                        exchange_id, orderbooks[pair1], orderbooks[pair2], orderbooks[pair3],
                        pair1, pair2, pair3
                    )
                    if opp:
                        opportunities.append(opp)
                        
                except Exception as e:
                    logger.error(f"Triangular calculation failed for {pair1}-{pair2}-{pair3}: {e}")
        
        return opportunities
    
    async def _calculate_triangular_profit(self, exchange_id: str, ob1: Dict, ob2: Dict, ob3: Dict,
                                         pair1: str, pair2: str, pair3: str) -> Optional[OpportunitySignal]:
        """Calculate profit from triangular arbitrage"""
        try:
            start_amount = Decimal('1.0')  # Start with 1 unit of base currency
            
            # Parse currency pairs
            base1, quote1 = pair1.split('/')
            base2, quote2 = pair2.split('/')
            base3, quote3 = pair3.split('/')
            
            # Try both directions around the triangle
            for direction in ['forward', 'reverse']:
                try:
                    if direction == 'forward':
                        # Example: BTC -> USDT -> ETH -> BTC
                        # Step 1: Sell BTC for USDT
                        step1_price = Decimal(str(ob1['bids'][0][0]))
                        amount_after_step1 = start_amount * step1_price
                        
                        # Step 2: Buy ETH with USDT  
                        step2_price = Decimal(str(ob2['asks'][0][0]))
                        amount_after_step2 = amount_after_step1 / step2_price
                        
                        # Step 3: Sell ETH for BTC
                        step3_price = Decimal(str(ob3['bids'][0][0]))
                        final_amount = amount_after_step2 * step3_price
                        
                    else:
                        # Reverse direction
                        step1_price = Decimal(str(ob1['asks'][0][0]))
                        amount_after_step1 = start_amount / step1_price
                        
                        step2_price = Decimal(str(ob2['bids'][0][0]))
                        amount_after_step2 = amount_after_step1 * step2_price
                        
                        step3_price = Decimal(str(ob3['asks'][0][0]))
                        final_amount = amount_after_step2 / step3_price
                    
                    profit = final_amount - start_amount
                    profit_percentage = profit / start_amount
                    
                    if profit_percentage >= self.min_profit_thresholds['triangular']:
                        confidence = self._calculate_triangular_confidence(
                            profit_percentage, exchange_id, [pair1, pair2, pair3]
                        )
                        
                        if confidence > 0.6:
                            return OpportunitySignal(
                                strategy_type='triangular',
                                confidence=confidence,
                                expected_profit=profit * 1000,  # Scale to $1000 trade
                                profit_percentage=profit_percentage,
                                execution_complexity=6,  # Three trades required
                                time_sensitivity=9,      # Very time sensitive
                                required_capital=Decimal('1000'),
                                risk_score=0.3,          # Lower risk (same exchange)
                                metadata={
                                    'exchange': exchange_id,
                                    'pairs': [pair1, pair2, pair3],
                                    'direction': direction,
                                    'start_amount': start_amount,
                                    'final_amount': final_amount
                                }
                            )
                except Exception:
                    continue
            
        except Exception as e:
            logger.error(f"Triangular profit calculation failed: {e}")
        
        return None
    
    def _calculate_triangular_confidence(self, profit_pct: Decimal, exchange_id: str, pairs: List[str]) -> float:
        """Calculate confidence for triangular arbitrage"""
        base_confidence = 0.6
        
        # Profit factor
        profit_factor = min(float(profit_pct) * 50, 1.0)
        
        # Exchange factor (tier 1 exchanges more reliable)
        if exchange_id in self.exchange_manager.tier1_exchanges:
            exchange_factor = 1.0
        elif exchange_id in self.exchange_manager.tier2_exchanges:
            exchange_factor = 0.9
        else:
            exchange_factor = 0.7
        
        # Pair factor (major pairs more reliable)
        major_pairs = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ETH/BTC', 'BNB/BTC', 'BNB/ETH']
        major_count = sum(1 for pair in pairs if pair in major_pairs)
        pair_factor = 0.6 + (major_count / len(pairs)) * 0.4
        
        confidence = base_confidence * profit_factor * exchange_factor * pair_factor
        return min(confidence, 1.0)
    
    async def detect_cross_chain_arbitrage(self) -> List[OpportunitySignal]:
        """Detect cross-chain arbitrage opportunities"""
        opportunities = []
        
        if not self.dex_manager or not self.dex_manager.w3_connections:
            return opportunities
        
        # Major tokens available across chains
        cross_chain_tokens = ['WETH', 'USDT', 'USDC']
        
        for token in cross_chain_tokens:
            try:
                cross_chain_opps = await self.dex_manager.estimate_cross_chain_profit(
                    token, Decimal('1000')  # $1000 test amount
                )
                
                for opp in cross_chain_opps:
                    if opp['net_profit'] > 0:
                        profit_pct = opp['profit_pct']
                        
                        if profit_pct >= self.min_profit_thresholds['cross_chain']:
                            confidence = self._calculate_cross_chain_confidence(opp)
                            
                            if confidence > 0.5:
                                opportunity = OpportunitySignal(
                                    strategy_type='cross_chain',
                                    confidence=confidence,
                                    expected_profit=opp['net_profit'],
                                    profit_percentage=profit_pct,
                                    execution_complexity=8,  # Bridge + DEX trades
                                    time_sensitivity=5,      # Lower due to bridge times
                                    required_capital=opp['amount'],
                                    risk_score=0.6,          # Higher risk due to bridges
                                    metadata=opp
                                )
                                opportunities.append(opportunity)
                                
            except Exception as e:
                logger.error(f"Cross-chain detection failed for {token}: {e}")
        
        return opportunities
    
    def _calculate_cross_chain_confidence(self, opportunity: Dict) -> float:
        """Calculate confidence for cross-chain arbitrage"""
        base_confidence = 0.4
        
        # Profit factor
        profit_factor = min(float(opportunity['profit_pct']) * 20, 1.0)
        
        # Cost factor (lower costs = higher confidence)
        cost_ratio = float(opportunity['estimated_costs']) / float(opportunity['net_profit'])
        cost_factor = max(0.1, 1.0 - cost_ratio)
        
        # Chain factor (established chains more reliable)
        established_chains = ['ethereum', 'bsc', 'polygon']
        buy_chain = opportunity['buy_venue'].split('_')[0]
        sell_chain = opportunity['sell_venue'].split('_')[0]
        
        chain_factor = 1.0
        if buy_chain not in established_chains:
            chain_factor *= 0.8
        if sell_chain not in established_chains:
            chain_factor *= 0.8
        
        confidence = base_confidence * profit_factor * cost_factor * chain_factor
        return min(confidence, 1.0)
    
    async def detect_funding_rate_arbitrage(self, symbols: List[str]) -> List[OpportunitySignal]:
        """Detect funding rate arbitrage opportunities"""
        # Placeholder - would integrate with futures data
        return []
    
    async def detect_statistical_arbitrage(self, symbols: List[str]) -> List[OpportunitySignal]:
        """Detect statistical arbitrage opportunities"""
        # Placeholder - would implement mean reversion strategies
        return []
    
    async def detect_launch_arbitrage(self) -> List[OpportunitySignal]:
        """Detect new token launch arbitrage"""
        # Placeholder - would monitor new listings
        return []
    
    def _score_and_filter_opportunities(self, opportunities: List[OpportunitySignal]) -> List[OpportunitySignal]:
        """Score and filter opportunities by quality"""
        if not opportunities:
            return []
        
        # Calculate composite scores
        for opp in opportunities:
            # Composite score factors
            profit_score = min(float(opp.profit_percentage) * 100, 10.0) / 10.0
            confidence_score = opp.confidence
            speed_score = (11 - opp.execution_complexity) / 10.0
            risk_score = 1.0 - opp.risk_score
            
            # Weighted composite score
            opp.composite_score = (
                profit_score * 0.4 +
                confidence_score * 0.3 + 
                speed_score * 0.2 +
                risk_score * 0.1
            )
        
        # Filter and sort
        high_quality = [opp for opp in opportunities if opp.composite_score > 0.6]
        return sorted(high_quality, key=lambda x: x.composite_score, reverse=True)[:20]
    
    def _calculate_risk_score(self, buy_exchange: str, sell_exchange: str) -> float:
        """Calculate risk score for exchange pair"""
        base_risk = 0.3
        
        # Exchange tier risk adjustment
        tier1_exchanges = self.exchange_manager.tier1_exchanges
        tier2_exchanges = self.exchange_manager.tier2_exchanges
        
        if buy_exchange in tier1_exchanges and sell_exchange in tier1_exchanges:
            return base_risk
        elif buy_exchange in tier2_exchanges or sell_exchange in tier2_exchanges:
            return base_risk + 0.1
        else:
            return base_risk + 0.2
