#!/usr/bin/env python3
"""Enhanced main bot with multi-strategy detection"""
import asyncio
import signal
import sys
from pathlib import Path
from loguru import logger

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from src.enhanced.data.multi_exchange_manager import EnhancedExchangeManager
from src.dex.multi_chain_manager import MultiChainDEXManager
from src.strategies.multi_strategy_detector import MultiStrategyDetector

class EnhancedArbitrageBot:
    def __init__(self):
        self.exchange_manager = EnhancedExchangeManager()
        self.dex_manager = MultiChainDEXManager()
        self.strategy_detector = MultiStrategyDetector(
            self.exchange_manager, 
            self.dex_manager
        )
        self.running = True
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("🚀 Initializing Enhanced Arbitrage System...")
        
        await self.exchange_manager.initialize()
        await self.dex_manager.initialize()
        
        logger.success("✅ Enhanced system initialized!")
        
    async def run_detection_loop(self):
        """Main opportunity detection loop"""
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']
        
        while self.running:
            try:
                logger.info("🔍 Scanning for arbitrage opportunities...")
                
                opportunities = await self.strategy_detector.detect_all_opportunities(symbols)
                
                if opportunities:
                    logger.success(f"Found {len(opportunities)} high-quality opportunities!")
                    
                    for i, opp in enumerate(opportunities[:5], 1):
                        logger.info(f"#{i} {opp.strategy_type}: "
                                  f"{opp.profit_percentage:.3%} profit, "
                                  f"confidence: {opp.confidence:.2f}, "
                                  f"complexity: {opp.execution_complexity}/10")
                else:
                    logger.info("No opportunities found in this cycle")
                
            except Exception as e:
                logger.error(f"Detection loop error: {e}")
            
            await asyncio.sleep(10)
    
    async def run(self):
        """Run the enhanced bot"""
        await self.initialize()
        await self.run_detection_loop()

def signal_handler(sig, frame):
    logger.info("Shutting down Enhanced Arbitrage Bot...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    
    # Configure logging
    logger.add("logs/enhanced_bot.log", rotation="1 day", retention="7 days")
    logger.info("Starting Enhanced Arbitrage Bot...")
    
    bot = EnhancedArbitrageBot()
    asyncio.run(bot.run())
