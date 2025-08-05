import asyncio
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
import time

from ..strategies.dex_arbitrage.engine import DEXArbitrageEngine
from ..strategies.liquidation_hunting.hunter import LiquidationHunter
from ..strategies.sandwich_attacks.coordinator import SandwichCoordinator
from ..strategies.bridge_arbitrage.bridge_monitor import BridgeArbitrageMonitor
from ..strategies.governance_sniping.vote_tracker import GovernanceSniper
from ..strategies.nft_arbitrage.marketplace_scanner import NFTArbitrageEngine
from ..strategies.options_arbitrage.options_scanner import OptionsArbitrageEngine
from ..strategies.protocol_exploits.new_protocol_scanner import ProtocolExploiter

logger = logging.getLogger(__name__)

class StrategyExecutor:
    def __init__(self, empire_controller):
        self.empire_controller = empire_controller
        self.strategies = {}
        self.strategy_performance = {}
        self.execution_queue = asyncio.Queue()
        self.is_running = False
        
    async def initialize(self):
        logger.info("Initializing Strategy Executor")
        
        self.strategies = {
            "dex_arbitrage": DEXArbitrageEngine(
                self.empire_controller.chain_manager,
                self.empire_controller.price_aggregator
            ),
            "liquidation_hunting": LiquidationHunter(
                self.empire_controller.chain_manager
            ),
            "sandwich_attacks": SandwichCoordinator(
                self.empire_controller.chain_manager
            ),
            "bridge_arbitrage": BridgeArbitrageMonitor(
                self.empire_controller.chain_manager
            ),
            "governance_sniping": GovernanceSniper(
                self.empire_controller.chain_manager
            ),
            "nft_arbitrage": NFTArbitrageEngine(),
            "options_arbitrage": OptionsArbitrageEngine(),
            "protocol_exploits": ProtocolExploiter()
        }
        
        for strategy_name, strategy in self.strategies.items():
            await strategy.initialize()
            self.strategy_performance[strategy_name] = {
                "trades": 0,
                "profit": Decimal("0"),
                "success_rate": 0.0,
                "avg_execution_time": 0.0
            }
        
        logger.info("Strategy Executor initialized")
    
    async def start_all_strategies(self):
        if self.is_running:
            return
            
        logger.info("Starting all strategies")
        self.is_running = True
        
        for strategy in self.strategies.values():
            await strategy.start()
        
        asyncio.create_task(self._execution_loop())
        asyncio.create_task(self._performance_monitoring_loop())
        
        logger.info("All strategies started")
    
    async def stop_all_strategies(self):
        if not self.is_running:
            return
            
        logger.info("Stopping all strategies")
        self.is_running = False
        
        for strategy in self.strategies.values():
            await strategy.stop()
        
        logger.info("All strategies stopped")
    
    async def execute_strategy(self, strategy_name: str, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        if strategy_name not in self.strategies:
            return {"success": False, "error": f"Strategy {strategy_name} not found"}
        
        start_time = time.time()
        
        try:
            strategy = self.strategies[strategy_name]
            
            if hasattr(strategy, 'execute_arbitrage'):
                result = await strategy.execute_arbitrage(opportunity)
            elif hasattr(strategy, 'execute_liquidation'):
                result = await strategy.execute_liquidation(opportunity)
            elif hasattr(strategy, 'execute_sandwich'):
                result = await strategy.execute_sandwich(opportunity)
            else:
                result = await strategy.execute(opportunity)
            
            execution_time = time.time() - start_time
            
            await self._update_strategy_performance(strategy_name, result, execution_time)
            
            return result
            
        except Exception as e:
            logger.error(f"Strategy execution error for {strategy_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def _execution_loop(self):
        while self.is_running:
            try:
                opportunity = await asyncio.wait_for(self.execution_queue.get(), timeout=1.0)
                
                result = await self.execute_strategy(
                    opportunity["strategy"],
                    opportunity["data"]
                )
                
                if result["success"] and result.get("profit", 0) > 1000:
                    logger.info(f"High-profit execution: ${result['profit']:.2f} from {opportunity['strategy']}")
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Execution loop error: {e}")
                await asyncio.sleep(1)
    
    async def _performance_monitoring_loop(self):
        while self.is_running:
            try:
                for strategy_name in self.strategies.keys():
                    performance = await self._calculate_strategy_performance(strategy_name)
                    self.strategy_performance[strategy_name] = performance
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _update_strategy_performance(self, strategy_name: str, result: Dict[str, Any], execution_time: float):
        perf = self.strategy_performance[strategy_name]
        
        perf["trades"] += 1
        
        if result["success"]:
            profit = Decimal(str(result.get("profit", 0)))
            perf["profit"] += profit
        
        total_time = perf["avg_execution_time"] * (perf["trades"] - 1) + execution_time
        perf["avg_execution_time"] = total_time / perf["trades"]
        
        success_count = sum(1 for _ in range(perf["trades"]) if result["success"])
        perf["success_rate"] = success_count / perf["trades"]
    
    async def _calculate_strategy_performance(self, strategy_name: str) -> Dict[str, Any]:
        strategy = self.strategies[strategy_name]
        
        base_performance = self.strategy_performance[strategy_name].copy()
        
        if hasattr(strategy, 'get_stats'):
            strategy_stats = strategy.get_stats()
            base_performance.update(strategy_stats)
        
        return base_performance
    
    async def get_all_performance(self) -> Dict[str, Any]:
        return {
            "strategies": self.strategy_performance.copy(),
            "total_profit": sum(perf["profit"] for perf in self.strategy_performance.values()),
            "total_trades": sum(perf["trades"] for perf in self.strategy_performance.values()),
            "overall_success_rate": self._calculate_overall_success_rate(),
            "active_strategies": len([s for s in self.strategies.values() if s.is_running])
        }
    
    def _calculate_overall_success_rate(self) -> float:
        total_trades = sum(perf["trades"] for perf in self.strategy_performance.values())
        if total_trades == 0:
            return 0.0
        
        weighted_success = sum(
            perf["success_rate"] * perf["trades"] 
            for perf in self.strategy_performance.values()
        )
        
        return weighted_success / total_trades
