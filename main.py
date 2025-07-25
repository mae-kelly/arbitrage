import asyncio
import signal
from loguru import logger
from src.data.exchange_manager import ExchangeManager
from src.detection.arbitrage_finder import ArbitrageFinder
from src.execution.trader import PaperTrader

class CryptoArbitrageBot:
    def __init__(self):
        self.exchange_manager = ExchangeManager()
        self.arbitrage_finder = ArbitrageFinder(self.exchange_manager)
        self.trader = PaperTrader()
        self.running = True
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing Crypto Arbitrage Bot...")
        await self.exchange_manager.initialize()
        logger.info("Bot initialized successfully!")
        
    async def run_monitoring(self):
        """Run price monitoring"""
        await self.exchange_manager.monitor_prices()
        
    async def run_arbitrage_detection(self):
        """Run arbitrage detection"""
        await self.arbitrage_finder.monitor_arbitrage()
        
    async def run_trading(self):
        """Run trading loop"""
        while self.running:
            try:
                opportunities = self.arbitrage_finder.get_best_opportunities(limit=3)
                
                for opp in opportunities:
                    if opp.profit_pct > 0.01:  # Only trade if profit > 1%
                        await self.trader.execute_arbitrage(opp)
                
                # Print stats every 30 seconds
                stats = self.trader.get_performance_stats()
                if stats['total_trades'] > 0:
                    logger.info(f"Performance: {stats['total_trades']} trades, "
                              f"${stats['total_profit']:.2f} profit "
                              f"({stats['profit_percentage']:.2f}%)")
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
            
            await asyncio.sleep(10)
    
    async def run(self):
        """Run the complete arbitrage bot"""
        await self.initialize()
        
        # Start all tasks
        tasks = [
            asyncio.create_task(self.run_monitoring()),
            asyncio.create_task(self.run_arbitrage_detection()),
            asyncio.create_task(self.run_trading())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Shutting down bot...")
            self.running = False
            await self.exchange_manager.close()

def signal_handler(sig, frame):
    logger.info("Received interrupt signal, shutting down...")
    exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.add("logs/arbitrage_bot.log", rotation="1 day", retention="7 days")
    logger.info("Starting Crypto Arbitrage Bot...")
    
    bot = CryptoArbitrageBot()
    asyncio.run(bot.run())
