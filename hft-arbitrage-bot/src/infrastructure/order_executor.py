import asyncio
import ccxt.async_support as ccxt
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time
import logging

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    FAILED = "failed"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

@dataclass
class Order:
    id: str
    symbol: str
    side: str
    amount: float
    price: float
    order_type: OrderType
    status: OrderStatus
    filled_amount: float
    remaining_amount: float
    average_price: float
    fee: float
    timestamp: float
    exchange: str

@dataclass
class ExecutionResult:
    success: bool
    order: Optional[Order]
    error_message: Optional[str]
    execution_time_ms: float

class OrderExecutor:
    def __init__(self, config: Dict):
        self.config = config
        self.exchanges = {}
        self.active_orders = {}
        self.execution_history = []
        self.max_slippage = config.get('max_slippage', 0.5)
        self.timeout_seconds = config.get('timeout_seconds', 30)
        
    async def initialize_exchanges(self):
        exchange_configs = self.config.get('exchanges', {})
        
        for exchange_name, config in exchange_configs.items():
            try:
                exchange_class = getattr(ccxt, exchange_name)
                self.exchanges[exchange_name] = exchange_class({
                    'apiKey': config['api_key'],
                    'secret': config['secret'],
                    'sandbox': config.get('sandbox', True),
                    'enableRateLimit': True,
                    'timeout': self.timeout_seconds * 1000,
                    'options': {
                        'defaultType': 'spot',
                        'adjustForTimeDifference': True
                    }
                })
                
                await self.exchanges[exchange_name].load_markets()
                logging.info(f"Initialized {exchange_name} exchange")
                
            except Exception as e:
                logging.error(f"Failed to initialize {exchange_name}: {e}")
    
    async def execute_market_order(
        self, 
        exchange: str, 
        symbol: str, 
        side: str, 
        amount: float,
        max_slippage_percent: float = None
    ) -> ExecutionResult:
        
        start_time = time.time()
        
        if exchange not in self.exchanges:
            return ExecutionResult(
                success=False,
                order=None,
                error_message=f"Exchange {exchange} not initialized",
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        if max_slippage_percent is None:
            max_slippage_percent = self.max_slippage
        
        try:
            exchange_obj = self.exchanges[exchange]
            
            current_price = await self.get_current_price(exchange, symbol)
            if not current_price:
                return ExecutionResult(
                    success=False,
                    order=None,
                    error_message="Could not fetch current price",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            orderbook = await exchange_obj.fetch_order_book(symbol, limit=5)
            
            if side == 'buy':
                best_price = orderbook['asks'][0][0] if orderbook['asks'] else current_price
                max_acceptable_price = current_price * (1 + max_slippage_percent / 100)
                if best_price > max_acceptable_price:
                    return ExecutionResult(
                        success=False,
                        order=None,
                        error_message=f"Slippage too high: {best_price} > {max_acceptable_price}",
                        execution_time_ms=(time.time() - start_time) * 1000
                    )
            else:
                best_price = orderbook['bids'][0][0] if orderbook['bids'] else current_price
                min_acceptable_price = current_price * (1 - max_slippage_percent / 100)
                if best_price < min_acceptable_price:
                    return ExecutionResult(
                        success=False,
                        order=None,
                        error_message=f"Slippage too high: {best_price} < {min_acceptable_price}",
                        execution_time_ms=(time.time() - start_time) * 1000
                    )
            
            ccxt_order = await exchange_obj.create_market_order(symbol, side, amount)
            
            order = Order(
                id=ccxt_order['id'],
                symbol=symbol,
                side=side,
                amount=amount,
                price=ccxt_order.get('price', 0),
                order_type=OrderType.MARKET,
                status=OrderStatus(ccxt_order['status']) if ccxt_order['status'] in [s.value for s in OrderStatus] else OrderStatus.PENDING,
                filled_amount=ccxt_order.get('filled', 0),
                remaining_amount=ccxt_order.get('remaining', amount),
                average_price=ccxt_order.get('average', 0),
                fee=ccxt_order.get('fee', {}).get('cost', 0),
                timestamp=time.time(),
                exchange=exchange
            )
            
            self.active_orders[order.id] = order
            self.execution_history.append(order)
            
            return ExecutionResult(
                success=True,
                order=order,
                error_message=None,
                execution_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            error_msg = f"Order execution failed: {str(e)}"
            logging.error(error_msg)
            
            return ExecutionResult(
                success=False,
                order=None,
                error_message=error_msg,
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    async def execute_limit_order(
        self,
        exchange: str,
        symbol: str,
        side: str,
        amount: float,
        price: float
    ) -> ExecutionResult:
        
        start_time = time.time()
        
        if exchange not in self.exchanges:
            return ExecutionResult(
                success=False,
                order=None,
                error_message=f"Exchange {exchange} not initialized",
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        try:
            exchange_obj = self.exchanges[exchange]
            
            ccxt_order = await exchange_obj.create_limit_order(symbol, side, amount, price)
            
            order = Order(
                id=ccxt_order['id'],
                symbol=symbol,
                side=side,
                amount=amount,
                price=price,
                order_type=OrderType.LIMIT,
                status=OrderStatus(ccxt_order['status']) if ccxt_order['status'] in [s.value for s in OrderStatus] else OrderStatus.PENDING,
                filled_amount=ccxt_order.get('filled', 0),
                remaining_amount=ccxt_order.get('remaining', amount),
                average_price=ccxt_order.get('average', 0),
                fee=ccxt_order.get('fee', {}).get('cost', 0),
                timestamp=time.time(),
                exchange=exchange
            )
            
            self.active_orders[order.id] = order
            self.execution_history.append(order)
            
            return ExecutionResult(
                success=True,
                order=order,
                error_message=None,
                execution_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            error_msg = f"Limit order failed: {str(e)}"
            logging.error(error_msg)
            
            return ExecutionResult(
                success=False,
                order=None,
                error_message=error_msg,
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    async def execute_arbitrage_orders(
        self,
        buy_exchange: str,
        sell_exchange: str,
        symbol: str,
        amount: float
    ) -> Tuple[ExecutionResult, ExecutionResult]:
        
        buy_task = asyncio.create_task(
            self.execute_market_order(buy_exchange, symbol, 'buy', amount)
        )
        
        sell_task = asyncio.create_task(
            self.execute_market_order(sell_exchange, symbol, 'sell', amount)
        )
        
        buy_result, sell_result = await asyncio.gather(buy_task, sell_task, return_exceptions=True)
        
        if isinstance(buy_result, Exception):
            buy_result = ExecutionResult(
                success=False,
                order=None,
                error_message=str(buy_result),
                execution_time_ms=0
            )
        
        if isinstance(sell_result, Exception):
            sell_result = ExecutionResult(
                success=False,
                order=None,
                error_message=str(sell_result),
                execution_time_ms=0
            )
        
        return buy_result, sell_result
    
    async def cancel_order(self, exchange: str, order_id: str, symbol: str) -> bool:
        if exchange not in self.exchanges:
            return False
        
        try:
            exchange_obj = self.exchanges[exchange]
            await exchange_obj.cancel_order(order_id, symbol)
            
            if order_id in self.active_orders:
                self.active_orders[order_id].status = OrderStatus.CANCELLED
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    async def get_order_status(self, exchange: str, order_id: str, symbol: str) -> Optional[Order]:
        if exchange not in self.exchanges:
            return None
        
        try:
            exchange_obj = self.exchanges[exchange]
            ccxt_order = await exchange_obj.fetch_order(order_id, symbol)
            
            order = Order(
                id=ccxt_order['id'],
                symbol=symbol,
                side=ccxt_order['side'],
                amount=ccxt_order['amount'],
                price=ccxt_order.get('price', 0),
                order_type=OrderType.LIMIT if ccxt_order['type'] == 'limit' else OrderType.MARKET,
                status=OrderStatus(ccxt_order['status']) if ccxt_order['status'] in [s.value for s in OrderStatus] else OrderStatus.PENDING,
                filled_amount=ccxt_order.get('filled', 0),
                remaining_amount=ccxt_order.get('remaining', 0),
                average_price=ccxt_order.get('average', 0),
                fee=ccxt_order.get('fee', {}).get('cost', 0),
                timestamp=ccxt_order.get('timestamp', time.time() * 1000) / 1000,
                exchange=exchange
            )
            
            if order_id in self.active_orders:
                self.active_orders[order_id] = order
            
            return order
            
        except Exception as e:
            logging.error(f"Failed to fetch order status {order_id}: {e}")
            return None
    
    async def get_current_price(self, exchange: str, symbol: str) -> Optional[float]:
        if exchange not in self.exchanges:
            return None
        
        try:
            exchange_obj = self.exchanges[exchange]
            ticker = await exchange_obj.fetch_ticker(symbol)
            return ticker.get('last') or ticker.get('close')
            
        except Exception as e:
            logging.error(f"Failed to fetch price for {symbol} on {exchange}: {e}")
            return None
    
    async def get_account_balance(self, exchange: str) -> Optional[Dict]:
        if exchange not in self.exchanges:
            return None
        
        try:
            exchange_obj = self.exchanges[exchange]
            balance = await exchange_obj.fetch_balance()
            return balance
            
        except Exception as e:
            logging.error(f"Failed to fetch balance from {exchange}: {e}")
            return None
    
    async def monitor_active_orders(self):
        while True:
            if not self.active_orders:
                await asyncio.sleep(1)
                continue
            
            tasks = []
            for order_id, order in list(self.active_orders.items()):
                if order.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]:
                    tasks.append(
                        self.get_order_status(order.exchange, order_id, order.symbol)
                    )
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Order):
                        if result.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                            if result.id in self.active_orders:
                                del self.active_orders[result.id]
            
            await asyncio.sleep(0.1)
    
    def get_execution_stats(self) -> Dict:
        if not self.execution_history:
            return {}
        
        successful_orders = [o for o in self.execution_history if o.status == OrderStatus.FILLED]
        failed_orders = [o for o in self.execution_history if o.status == OrderStatus.FAILED]
        
        return {
            'total_orders': len(self.execution_history),
            'successful_orders': len(successful_orders),
            'failed_orders': len(failed_orders),
            'success_rate': len(successful_orders) / len(self.execution_history) * 100,
            'active_orders': len(self.active_orders),
            'avg_fill_rate': sum(o.filled_amount / o.amount for o in successful_orders) / len(successful_orders) if successful_orders else 0
        }
    
    async def cleanup(self):
        for exchange in self.exchanges.values():
            await exchange.close()
