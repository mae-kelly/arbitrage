import asyncio
import logging
import signal
import sys
from typing import Dict, Optional
import json
from datetime import datetime

from core.arbitrage_engine import ArbitrageEngine
from core.flash_loan_manager import FlashLoanManager
from core.risk_manager import RiskManager
from ai.rl_agent import TradingRLAgent
from ai.price_predictor import PricePredictor
from infrastructure.market_data import MarketDataService
from infrastructure.order_executor import OrderExecutor

class ArbitrageBotApplication:
    def __init__(self, config_path: str = "config.json"):
        self.config = self.load_config(config_path)
        self.running = False
        
        self.market_data_service = None
        self.arbitrage_engine = None
        self.flash_loan_manager = None
        self.risk_manager = None
        self.rl_agent = None
        self.price_predictor = None
        self.order_executor = None
        
        self.performance_metrics = {
            'total_trades': 0,
            'successful_trades': 0,
            'total_profit': 0.0,
            'start_time': datetime.now()
        }
        
        self.setup_logging()
        
    def load_config(self, config_path: str) -> Dict:
        default_config = {
            "exchanges": {
                "binance": {
                    "api_key": "",
                    "secret": "",
                    "sandbox": True,
                    "websocket_enabled": True,
                    "websocket_url": "wss://stream.binance.com:9443/ws",
                    "symbols": ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
                }
            },
            "blockchain": {
                "ethereum": {
                    "rpc_url": "https://mainnet.infura.io/v3/YOUR_KEY",
                    "chain_id": 1,
                    "arbitrage_contract": "0x"
                }
            },
            "trading": {
                "min_profit_percentage": 0.5,
                "max_position_size": 1000,
                "max_slippage": 0.5
            },
            "risk_management": {
                "max_portfolio_risk": 0.02,
                "max_single_position": 0.1,
                "max_correlation": 0.7
            },
            "ai": {
                "state_dim": 158,
                "action_dim": 4,
                "hidden_size": 128,
                "learning_rate": 1e-3
            },
            "redis_url": "redis://localhost:6379",
            "clickhouse_url": "clickhouse://localhost:9000"
        }
        
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        except FileNotFoundError:
            logging.warning(f"Config file {config_path} not found, using defaults")
            
        return default_config
    
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('arbitrage_bot.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    async def initialize(self):
        logging.info("Initializing Arbitrage Bot...")
        
        self.market_data_service = MarketDataService(self.config)
        await self.market_data_service.start()
        
        self.arbitrage_engine = ArbitrageEngine(self.config['trading'])
        await self.arbitrage_engine.initialize_exchanges()
        
        self.flash_loan_manager = FlashLoanManager(
            self.config['blockchain']['ethereum']['rpc_url'],
            self.config['blockchain']['ethereum']['chain_id']
        )
        
        self.risk_manager = RiskManager(self.config['risk_management'])
        
        self.rl_agent = TradingRLAgent(self.config['ai'])
        
        self.price_predictor = PricePredictor(self.config['ai'])
        
        self.order_executor = OrderExecutor(self.config)
        await self.order_executor.initialize_exchanges()
        
        asyncio.create_task(self.order_executor.monitor_active_orders())
        
        logging.info("All components initialized successfully")
    
    async def run_arbitrage_loop(self):
        logging.info("Starting arbitrage loop...")
        
        while self.running:
            try:
                opportunities = await self.arbitrage_engine.scan_arbitrage_opportunities()
                
                for opportunity in opportunities[:5]:
                    await self.process_arbitrage_opportunity(opportunity)
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logging.error(f"Error in arbitrage loop: {e}")
                await asyncio.sleep(1)
    
    async def process_arbitrage_opportunity(self, opportunity):
        try:
            trade_valid = await self.risk_manager.validate_trade(
                opportunity.token_pair,
                opportunity.volume,
                opportunity.buy_price
            )
            
            if not trade_valid:
                logging.debug(f"Trade rejected by risk manager: {opportunity.token_pair}")
                return
            
            market_data = await self.get_current_market_data()
            rl_action = self.rl_agent.select_action(market_data)
            
            position_size_multiplier = abs(rl_action['position_size'])
            adjusted_volume = opportunity.volume * position_size_multiplier
            
            prediction = self.price_predictor.predict_price(opportunity.token_pair)
            if prediction and prediction.confidence < 0.6:
                logging.debug(f"Low confidence prediction for {opportunity.token_pair}")
                return
            
            success = await self.execute_arbitrage_with_flash_loan(opportunity, adjusted_volume)
            
            if success:
                self.performance_metrics['successful_trades'] += 1
                self.performance_metrics['total_profit'] += opportunity.net_profit
                
                reward = self.rl_agent.update_reward(
                    portfolio_value=1000000 + self.performance_metrics['total_profit'],
                    trade_executed=True,
                    profit=opportunity.net_profit
                )
                
                next_market_data = await self.get_current_market_data()
                self.rl_agent.store_experience(next_market_data, reward)
                
                logging.info(f"Successful arbitrage: {opportunity.net_profit:.2f} profit")
            
            self.performance_metrics['total_trades'] += 1
            
            if self.performance_metrics['total_trades'] % 100 == 0:
                self.rl_agent.train_agent()
                
        except Exception as e:
            logging.error(f"Error processing arbitrage opportunity: {e}")
    
    async def execute_arbitrage_with_flash_loan(self, opportunity, volume: float) -> bool:
        try:
            if opportunity.source_exchange == opportunity.target_exchange:
                return False
            
            arbitrage_params = {
                'asset_address': '0xA0b86a33E6441e6e80D5E8B0B8d0EEb2C8C3C0e1',
                'dex_addresses': ['0xDEX1', '0xDEX2'],
                'min_profit': opportunity.net_profit
            }
            
            success = await self.flash_loan_manager.execute_flash_loan_arbitrage(
                opportunity.token_pair.split('/')[0],
                volume,
                arbitrage_params
            )
            
            return success
            
        except Exception as e:
            logging.error(f"Flash loan arbitrage failed: {e}")
            return False
    
    async def get_current_market_data(self) -> Dict:
        try:
            market_data = {}
            
            symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
            for symbol in symbols:
                ticker = await self.market_data_service.get_latest_ticker('binance', symbol)
                if ticker:
                    market_data[symbol] = {
                        'price': ticker.last,
                        'volume': ticker.volume,
                        'bid': ticker.bid,
                        'ask': ticker.ask,
                        'spread': (ticker.ask - ticker.bid) / ticker.bid,
                        'volatility': 0.02
                    }
            
            market_data['portfolio'] = {
                'total_value': 1000000 + self.performance_metrics['total_profit'],
                'available_balance': 500000,
                'num_positions': len(self.risk_manager.positions),
                'unrealized_pnl': 0
            }
            
            return market_data
            
        except Exception as e:
            logging.error(f"Error getting market data: {e}")
            return {}
    
    async def run_ai_training_loop(self):
        logging.info("Starting AI training loop...")
        
        while self.running:
            try:
                market_data = await self.get_current_market_data()
                
                for symbol in ['BTC/USDT', 'ETH/USDT']:
                    ticker = await self.market_data_service.get_latest_ticker('binance', symbol)
                    if ticker:
                        self.price_predictor.add_price_data(symbol, ticker.timestamp, {
                            'open': ticker.last,
                            'high': ticker.last * 1.01,
                            'low': ticker.last * 0.99,
                            'close': ticker.last,
                            'volume': ticker.volume
                        })
                
                if self.performance_metrics['total_trades'] % 1000 == 0 and self.performance_metrics['total_trades'] > 0:
                    for symbol in ['BTC/USDT', 'ETH/USDT']:
                        self.price_predictor.train_model(symbol, epochs=50)
                
                await asyncio.sleep(60)
                
            except Exception as e:
                logging.error(f"Error in AI training loop: {e}")
                await asyncio.sleep(10)
    
    async def run_monitoring_loop(self):
        while self.running:
            try:
                runtime = datetime.now() - self.performance_metrics['start_time']
                success_rate = (self.performance_metrics['successful_trades'] / 
                              max(self.performance_metrics['total_trades'], 1)) * 100
                
                logging.info(f"Performance - Runtime: {runtime}, "
                           f"Total Trades: {self.performance_metrics['total_trades']}, "
                           f"Success Rate: {success_rate:.2f}%, "
                           f"Total Profit: ${self.performance_metrics['total_profit']:.2f}")
                
                risk_metrics = await self.risk_manager.calculate_portfolio_risk()
                logging.info(f"Risk Metrics - VaR 95%: {risk_metrics.var_95:.4f}, "
                           f"Sharpe: {risk_metrics.sharpe_ratio:.2f}")
                
                execution_stats = self.order_executor.get_execution_stats()
                if execution_stats:
                    logging.info(f"Execution Stats - Success Rate: {execution_stats.get('success_rate', 0):.2f}%, "
                               f"Active Orders: {execution_stats.get('active_orders', 0)}")
                
                rl_performance = self.rl_agent.get_performance_metrics()
                if rl_performance:
                    logging.info(f"RL Agent - Avg Reward: {rl_performance.get('avg_reward', 0):.4f}, "
                               f"Episodes: {rl_performance.get('total_episodes', 0)}")
                
                await asyncio.sleep(300)
                
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def start(self):
        await self.initialize()
        
        self.running = True
        
        tasks = [
            asyncio.create_task(self.run_arbitrage_loop()),
            asyncio.create_task(self.run_ai_training_loop()),
            asyncio.create_task(self.run_monitoring_loop())
        ]
        
        await asyncio.gather(*tasks)
    
    async def stop(self):
        logging.info("Shutting down Arbitrage Bot...")
        self.running = False
        
        if self.market_data_service:
            await self.market_data_service.stop()
        
        if self.arbitrage_engine:
            await self.arbitrage_engine.cleanup()
        
        if self.order_executor:
            await self.order_executor.cleanup()
        
        logging.info("Shutdown complete")
    
    def signal_handler(self, signum, frame):
        logging.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(self.stop())

async def main():
    app = ArbitrageBotApplication()
    
    signal.signal(signal.SIGINT, app.signal_handler)
    signal.signal(signal.SIGTERM, app.signal_handler)
    
    try:
        await app.start()
    except KeyboardInterrupt:
        await app.stop()
    except Exception as e:
        logging.error(f"Application error: {e}")
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
