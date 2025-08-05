#!/usr/bin/env python3

import asyncio
import argparse
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.empire_controller import EmpireController
from src.core.strategy_executor import StrategyExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_all_strategies():
    logger.info("Starting all MEV strategies")
    
    empire = EmpireController()
    await empire.initialize()
    
    await empire.start()
    
    logger.info("All strategies started successfully")
    
    try:
        while True:
            performance = await empire.get_performance_metrics()
            logger.info(f"Total profit: ${performance['total_profit']:.2f}")
            logger.info(f"Trades executed: {performance['trades_executed']}")
            logger.info(f"Success rate: {performance.get('success_rate', 0):.1%}")
            
            await asyncio.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
        await empire.stop()

async def start_specific_strategy(strategy_name: str):
    logger.info(f"Starting strategy: {strategy_name}")
    
    empire = EmpireController()
    await empire.initialize()
    
    strategy_executor = StrategyExecutor(empire)
    await strategy_executor.initialize()
    
    if strategy_name in strategy_executor.strategies:
        strategy = strategy_executor.strategies[strategy_name]
        await strategy.start()
        logger.info(f"Strategy {strategy_name} started")
        
        try:
            while True:
                stats = strategy.get_stats() if hasattr(strategy, 'get_stats') else {}
                logger.info(f"{strategy_name} stats: {stats}")
                await asyncio.sleep(30)
                
        except KeyboardInterrupt:
            await strategy.stop()
            logger.info(f"Strategy {strategy_name} stopped")
    else:
        logger.error(f"Strategy {strategy_name} not found")

async def main():
    parser = argparse.ArgumentParser(description="Start MEV Empire strategies")
    parser.add_argument("--strategy", type=str, help="Start specific strategy")
    parser.add_argument("--all", action="store_true", help="Start all strategies")
    
    args = parser.parse_args()
    
    if args.all or not args.strategy:
        await start_all_strategies()
    else:
        await start_specific_strategy(args.strategy)

if __name__ == "__main__":
    asyncio.run(main())
