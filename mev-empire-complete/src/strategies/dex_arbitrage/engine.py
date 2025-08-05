import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import time

from .route_optimizer import RouteOptimizer
from .dex_scanner import DEXScanner
from .cross_chain_scanner import CrossChainScanner
from ...utils.web3_utils import Web3Utils
from ...utils.math_utils import calculate_profit_after_gas

logger = logging.getLogger(__name__)

class DEXArbitrageEngine:
    def __init__(self, chain_manager, price_aggregator):
        self.chain_manager = chain_manager
        self.price_aggregator = price_aggregator
        self.route_optimizer = RouteOptimizer()
        self.dex_scanner = DEXScanner()
        self.cross_chain_scanner = CrossChainScanner()
        self.web3_utils = Web3Utils()
        
        self.min_profit_threshold = Decimal("0.005")
        self.max_position_size = Decimal("1000000")
        self.gas_price_multiplier = Decimal("1.2")
        
        self.is_running = False
        self.opportunities_found = 0
        self.trades_executed = 0
        
    async def initialize(self):
        logger.info("Initializing DEX Arbitrage Engine")
        
        await self.route_optimizer.initialize()
        await self.dex_scanner.initialize()
        await self.cross_chain_scanner.initialize()
        
        logger.info("DEX Arbitrage Engine initialized")
    
    async def start(self):
        if self.is_running:
            return
            
        logger.info("Starting DEX Arbitrage Engine")
        self.is_running = True
        
        await self.dex_scanner.start()
        await self.cross_chain_scanner.start()
        
        asyncio.create_task(self._arbitrage_loop())
        asyncio.create_task(self._optimization_loop())
        
        logger.info("DEX Arbitrage Engine started")
    
    async def stop(self):
        if not self.is_running:
            return
            
        logger.info("Stopping DEX Arbitrage Engine")
        self.is_running = False
        
        await self.dex_scanner.stop()
        await self.cross_chain_scanner.stop()
        
        logger.info("DEX Arbitrage Engine stopped")
    
    async def execute_arbitrage(self, opportunity: Dict) -> Dict:
        try:
            start_time = time.time()
            
            route = await self.route_optimizer.find_optimal_route(
                opportunity["token_in"],
                opportunity["token_out"],
                opportunity["amount"],
                opportunity["exchanges"]
            )
            
            if not route or route["profit"] < self.min_profit_threshold:
                return {"success": False, "reason": "Insufficient profit"}
            
            gas_cost = await self._estimate_gas_cost(route)
            net_profit = route["profit"] - gas_cost
            
            if net_profit <= 0:
                return {"success": False, "reason": "Gas cost exceeds profit"}
            
            execution_result = await self._execute_flash_loan_arbitrage(route)
            
            execution_time = time.time() - start_time
            
            if execution_result["success"]:
                self.trades_executed += 1
                logger.info(f"Arbitrage executed: {net_profit} profit in {execution_time:.2f}s")
            
            return {
                "success": execution_result["success"],
                "profit": float(net_profit),
                "gas_cost": float(gas_cost),
                "execution_time": execution_time,
                "route": route,
                "tx_hash": execution_result.get("tx_hash")
            }
            
        except Exception as e:
            logger.error(f"Arbitrage execution error: {e}")
            return {"success": False, "error": str(e)}
    
    async def scan_opportunities(self) -> List[Dict]:
        opportunities = []
        
        try:
            single_chain_opportunities = await self._scan_single_chain_opportunities()
            cross_chain_opportunities = await self._scan_cross_chain_opportunities()
            
            opportunities.extend(single_chain_opportunities)
            opportunities.extend(cross_chain_opportunities)
            
            opportunities = await self._filter_opportunities(opportunities)
            opportunities.sort(key=lambda x: x["profit_potential"], reverse=True)
            
            self.opportunities_found += len(opportunities)
            
        except Exception as e:
            logger.error(f"Opportunity scanning error: {e}")
        
        return opportunities[:10]
    
    async def _arbitrage_loop(self):
        while self.is_running:
            try:
                opportunities = await self.scan_opportunities()
                
                for opportunity in opportunities:
                    if opportunity["profit_potential"] > self.min_profit_threshold:
                        result = await self.execute_arbitrage(opportunity)
                        
                        if result["success"]:
                            logger.info(f"Arbitrage profit: ${result['profit']:.2f}")
                        else:
                            logger.debug(f"Arbitrage failed: {result.get('reason', 'Unknown')}")
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Arbitrage loop error: {e}")
                await asyncio.sleep(1)
    
    async def _optimization_loop(self):
        while self.is_running:
            try:
                await self._optimize_gas_price()
                await self._update_dex_fees()
                await self._calibrate_profit_thresholds()
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Optimization loop error: {e}")
                await asyncio.sleep(60)
    
    async def _scan_single_chain_opportunities(self) -> List[Dict]:
        opportunities = []
        
        for chain_id in [1, 137, 56, 42161, 43114]:
            chain_opportunities = await self.dex_scanner.scan_chain(chain_id)
            opportunities.extend(chain_opportunities)
        
        return opportunities
    
    async def _scan_cross_chain_opportunities(self) -> List[Dict]:
        return await self.cross_chain_scanner.scan_cross_chain_arbitrage()
    
    async def _filter_opportunities(self, opportunities: List[Dict]) -> List[Dict]:
        filtered = []
        
        for opp in opportunities:
            if (opp["amount"] <= self.max_position_size and 
                opp["profit_potential"] >= self.min_profit_threshold and
                await self._validate_liquidity(opp)):
                filtered.append(opp)
        
        return filtered
    
    async def _execute_flash_loan_arbitrage(self, route: Dict) -> Dict:
        try:
            flash_loan_contract = await self.web3_utils.get_flash_loan_contract(
                route["chain_id"]
            )
            
            execution_data = self._encode_arbitrage_data(route)
            
            tx = await flash_loan_contract.functions.executeFlashLoan(
                route["token_in"],
                route["amount"],
                execution_data
            ).build_transaction({
                "gas": route["gas_limit"],
                "gasPrice": route["gas_price"]
            })
            
            signed_tx = await self.web3_utils.sign_transaction(tx, route["chain_id"])
            tx_hash = await self.web3_utils.send_transaction(signed_tx, route["chain_id"])
            
            receipt = await self.web3_utils.wait_for_receipt(tx_hash, route["chain_id"])
            
            return {
                "success": receipt["status"] == 1,
                "tx_hash": tx_hash.hex(),
                "gas_used": receipt["gasUsed"]
            }
            
        except Exception as e:
            logger.error(f"Flash loan execution error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _estimate_gas_cost(self, route: Dict) -> Decimal:
        base_gas = 200000
        swap_gas = len(route["path"]) * 100000
        total_gas = base_gas + swap_gas
        
        gas_price = await self.web3_utils.get_gas_price(route["chain_id"])
        gas_price_wei = int(gas_price * self.gas_price_multiplier)
        
        gas_cost_wei = total_gas * gas_price_wei
        gas_cost_eth = Decimal(str(gas_cost_wei)) / Decimal("1e18")
        
        eth_price = await self.price_aggregator.get_price("ETH", "USD")
        gas_cost_usd = gas_cost_eth * Decimal(str(eth_price))
        
        return gas_cost_usd
    
    def _encode_arbitrage_data(self, route: Dict) -> bytes:
        return b""
    
    async def _validate_liquidity(self, opportunity: Dict) -> bool:
        return True
    
    async def _optimize_gas_price(self):
        pass
    
    async def _update_dex_fees(self):
        pass
    
    async def _calibrate_profit_thresholds(self):
        pass
    
    def get_stats(self) -> Dict:
        return {
            "opportunities_found": self.opportunities_found,
            "trades_executed": self.trades_executed,
            "success_rate": self.trades_executed / max(self.opportunities_found, 1),
            "is_running": self.is_running
        }
