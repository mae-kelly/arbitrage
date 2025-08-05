#!/usr/bin/env python3

import asyncio
import logging
import sys
from pathlib import Path
import json
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from src.empire_controller import EmpireController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmpireMonitor:
    def __init__(self):
        self.empire = None
        self.monitoring = False
        
    async def initialize(self):
        logger.info("Initializing Empire Monitor")
        self.empire = EmpireController()
        await self.empire.initialize()
        
    async def start_monitoring(self):
        if not self.empire:
            await self.initialize()
            
        logger.info("Starting Empire monitoring")
        self.monitoring = True
        
        await asyncio.gather(
            self.performance_monitor(),
            self.health_monitor(),
            self.profit_monitor(),
            self.strategy_monitor()
        )
    
    async def performance_monitor(self):
        while self.monitoring:
            try:
                performance = await self.empire.get_performance_metrics()
                
                logger.info("=== PERFORMANCE METRICS ===")
                logger.info(f"Total Profit: ${performance.get('total_profit', 0):,.2f}")
                logger.info(f"Trades Executed: {performance.get('trades_executed', 0):,}")
                logger.info(f"Runtime: {performance.get('runtime_hours', 0):.1f} hours")
                logger.info(f"Profit/Hour: ${performance.get('profit_per_hour', 0):,.2f}")
                logger.info(f"Success Rate: {performance.get('success_rate', 0):.1%}")
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def health_monitor(self):
        while self.monitoring:
            try:
                health = await self.empire.health_check()
                
                if not health.get("healthy", False):
                    logger.warning("=== HEALTH CHECK FAILED ===")
                    for service, status in health.get("checks", {}).items():
                        if not status:
                            logger.warning(f"Service {service} is unhealthy")
                
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def profit_monitor(self):
        last_profit = 0
        
        while self.monitoring:
            try:
                performance = await self.empire.get_performance_metrics()
                current_profit = performance.get('total_profit', 0)
                
                if current_profit > last_profit + 1000:
                    profit_increase = current_profit - last_profit
                    logger.info(f"🚀 PROFIT ALERT: +${profit_increase:,.2f} (Total: ${current_profit:,.2f})")
                    last_profit = current_profit
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Profit monitoring error: {e}")
                await asyncio.sleep(15)
    
    async def strategy_monitor(self):
        while self.monitoring:
            try:
                if hasattr(self.empire, 'strategy_executor') and self.empire.strategy_executor:
                    strategy_performance = await self.empire.strategy_executor.get_all_performance()
                    
                    logger.info("=== STRATEGY PERFORMANCE ===")
                    for strategy_name, perf in strategy_performance.get("strategies", {}).items():
                        logger.info(f"{strategy_name}: {perf.get('trades', 0)} trades, ${float(perf.get('profit', 0)):,.2f} profit")
                
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Strategy monitoring error: {e}")
                await asyncio.sleep(120)
    
    async def stop_monitoring(self):
        logger.info("Stopping Empire monitoring")
        self.monitoring = False

async def main():
    monitor = EmpireMonitor()
    
    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
        await monitor.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
