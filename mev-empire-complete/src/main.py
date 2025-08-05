import asyncio
import signal
import sys
import logging
from typing import Optional
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from .empire_controller import EmpireController
from .core.strategy_executor import StrategyExecutor
from .monitoring.dashboard import create_dashboard
from .utils.logger import setup_logging
from .utils.security_utils import SecurityManager

logger = logging.getLogger(__name__)

class MEVEmpire:
    def __init__(self):
        self.controller: Optional[EmpireController] = None
        self.strategy_executor: Optional[StrategyExecutor] = None
        self.app: Optional[FastAPI] = None
        self.is_running = False
        
    async def initialize(self):
        setup_logging()
        logger.info("Initializing MEV Empire")
        
        self.controller = EmpireController()
        await self.controller.initialize()
        
        self.strategy_executor = StrategyExecutor(self.controller)
        await self.strategy_executor.initialize()
        
        self.app = create_dashboard(self.controller)
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("MEV Empire initialized successfully")
    
    async def start(self):
        if self.is_running:
            return
            
        logger.info("Starting MEV Empire")
        self.is_running = True
        
        await self.controller.start()
        await self.strategy_executor.start_all_strategies()
        
        config = uvicorn.Config(
            app=self.app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True
        )
        server = uvicorn.Server(config)
        
        tasks = [
            asyncio.create_task(server.serve()),
            asyncio.create_task(self._monitor_performance()),
            asyncio.create_task(self._health_check_loop())
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop(self):
        if not self.is_running:
            return
            
        logger.info("Stopping MEV Empire")
        self.is_running = False
        
        if self.strategy_executor:
            await self.strategy_executor.stop_all_strategies()
        
        if self.controller:
            await self.controller.stop()
        
        logger.info("MEV Empire stopped")
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown")
        asyncio.create_task(self.stop())
    
    async def _monitor_performance(self):
        while self.is_running:
            try:
                performance_data = await self.controller.get_performance_metrics()
                logger.info(f"Performance: {performance_data}")
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _health_check_loop(self):
        while self.is_running:
            try:
                health_status = await self.controller.health_check()
                if not health_status["healthy"]:
                    logger.warning(f"Health check failed: {health_status}")
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(30)

async def main():
    empire = MEVEmpire()
    
    try:
        await empire.initialize()
        await empire.start()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await empire.stop()

if __name__ == "__main__":
    asyncio.run(main())
