import asyncio
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
import time

from .core.strategy_executor import StrategyExecutor
from .core.opportunity_aggregator import OpportunityAggregator
from .core.profit_optimizer import ProfitOptimizer
from .core.capital_allocator import CapitalAllocator
from .core.risk_manager import RiskManager
from .core.performance_tracker import PerformanceTracker
from .data.price_aggregator import PriceAggregator
from .infrastructure.multi_chain_manager import MultiChainManager
from .monitoring.alert_system import AlertSystem
from .utils.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class EmpireController:
    def __init__(self):
        self.strategy_executor: Optional[StrategyExecutor] = None
        self.opportunity_aggregator: Optional[OpportunityAggregator] = None
        self.profit_optimizer: Optional[ProfitOptimizer] = None
        self.capital_allocator: Optional[CapitalAllocator] = None
        self.risk_manager: Optional[RiskManager] = None
        self.performance_tracker: Optional[PerformanceTracker] = None
        self.price_aggregator: Optional[PriceAggregator] = None
        self.chain_manager: Optional[MultiChainManager] = None
        self.alert_system: Optional[AlertSystem] = None
        self.cache_manager: Optional[CacheManager] = None
        
        self.is_running = False
        self.start_time = None
        self.total_profit = Decimal("0")
        self.trades_executed = 0
        
    async def initialize(self):
        logger.info("Initializing Empire Controller")
        
        self.cache_manager = CacheManager()
        await self.cache_manager.initialize()
        
        self.chain_manager = MultiChainManager()
        await self.chain_manager.initialize()
        
        self.price_aggregator = PriceAggregator(self.chain_manager)
        await self.price_aggregator.initialize()
        
        self.risk_manager = RiskManager()
        await self.risk_manager.initialize()
        
        self.capital_allocator = CapitalAllocator(self.risk_manager)
        await self.capital_allocator.initialize()
        
        self.profit_optimizer = ProfitOptimizer(self.capital_allocator)
        await self.profit_optimizer.initialize()
        
        self.opportunity_aggregator = OpportunityAggregator(
            self.price_aggregator, 
            self.chain_manager
        )
        await self.opportunity_aggregator.initialize()
        
        self.performance_tracker = PerformanceTracker()
        await self.performance_tracker.initialize()
        
        self.alert_system = AlertSystem()
        await self.alert_system.initialize()
        
        logger.info("Empire Controller initialized")
    
    async def start(self):
        if self.is_running:
            return
            
        logger.info("Starting Empire Controller")
        self.is_running = True
        self.start_time = time.time()
        
        await self.price_aggregator.start()
        await self.opportunity_aggregator.start()
        await self.performance_tracker.start()
        
        asyncio.create_task(self._coordination_loop())
        asyncio.create_task(self._monitoring_loop())
        
        logger.info("Empire Controller started")
    
    async def stop(self):
        if not self.is_running:
            return
            
        logger.info("Stopping Empire Controller")
        self.is_running = False
        
        if self.opportunity_aggregator:
            await self.opportunity_aggregator.stop()
        if self.price_aggregator:
            await self.price_aggregator.stop()
        if self.performance_tracker:
            await self.performance_tracker.stop()
        
        logger.info("Empire Controller stopped")
    
    async def execute_strategy(self, strategy_type: str, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        try:
            risk_assessment = await self.risk_manager.assess_opportunity(opportunity)
            if not risk_assessment["approved"]:
                return {"success": False, "reason": "Risk assessment failed"}
            
            optimal_allocation = await self.capital_allocator.calculate_allocation(
                strategy_type, opportunity
            )
            
            if optimal_allocation["amount"] <= 0:
                return {"success": False, "reason": "Insufficient allocation"}
            
            execution_plan = await self.profit_optimizer.optimize_execution(
                opportunity, optimal_allocation
            )
            
            result = await self._execute_trade(strategy_type, execution_plan)
            
            if result["success"]:
                self.total_profit += Decimal(str(result["profit"]))
                self.trades_executed += 1
                
                await self.performance_tracker.record_trade(result)
                await self.alert_system.notify_profit(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Strategy execution error: {e}")
            await self.alert_system.notify_error(str(e))
            return {"success": False, "error": str(e)}
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        if not self.performance_tracker:
            return {}
            
        runtime = time.time() - (self.start_time or time.time())
        
        return {
            "total_profit": float(self.total_profit),
            "trades_executed": self.trades_executed,
            "runtime_hours": runtime / 3600,
            "profit_per_hour": float(self.total_profit) / max(runtime / 3600, 1),
            "success_rate": await self.performance_tracker.get_success_rate(),
            "active_strategies": await self._get_active_strategies_count(),
            "system_health": await self.health_check()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        checks = {
            "chain_manager": await self.chain_manager.health_check() if self.chain_manager else False,
            "price_aggregator": await self.price_aggregator.health_check() if self.price_aggregator else False,
            "risk_manager": await self.risk_manager.health_check() if self.risk_manager else False,
            "cache_manager": await self.cache_manager.health_check() if self.cache_manager else False,
        }
        
        healthy = all(checks.values())
        
        return {
            "healthy": healthy,
            "checks": checks,
            "timestamp": time.time()
        }
    
    async def _coordination_loop(self):
        while self.is_running:
            try:
                opportunities = await self.opportunity_aggregator.get_opportunities()
                
                for opportunity in opportunities:
                    if opportunity["profit_potential"] > 0.005:
                        asyncio.create_task(
                            self.execute_strategy(opportunity["strategy"], opportunity)
                        )
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Coordination loop error: {e}")
                await asyncio.sleep(1)
    
    async def _monitoring_loop(self):
        while self.is_running:
            try:
                metrics = await self.get_performance_metrics()
                await self.performance_tracker.update_metrics(metrics)
                
                if metrics["profit_per_hour"] > 50000:
                    await self.alert_system.notify_high_performance(metrics)
                
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)
    
    async def _execute_trade(self, strategy_type: str, execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            if strategy_type == "dex_arbitrage":
                result = await self._execute_dex_arbitrage(execution_plan)
            elif strategy_type == "liquidation_hunting":
                result = await self._execute_liquidation(execution_plan)
            elif strategy_type == "bridge_arbitrage":
                result = await self._execute_bridge_arbitrage(execution_plan)
            else:
                result = await self._execute_generic_strategy(strategy_type, execution_plan)
            
            execution_time = time.time() - start_time
            result["execution_time"] = execution_time
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def _execute_dex_arbitrage(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "profit": 1000, "gas_cost": 50}
    
    async def _execute_liquidation(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "profit": 5000, "gas_cost": 100}
    
    async def _execute_bridge_arbitrage(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "profit": 2000, "gas_cost": 75}
    
    async def _execute_generic_strategy(self, strategy_type: str, plan: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "profit": 500, "gas_cost": 25}
    
    async def _get_active_strategies_count(self) -> int:
        return 12 if self.is_running else 0
