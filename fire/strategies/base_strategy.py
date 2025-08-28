# strategies/base_strategy.py

from abc import ABC, abstractmethod
from typing import Dict, Optional
import asyncio
from datetime import datetime

class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self.total_profit = 0
        self.total_trades = 0
        self.successful_trades = 0
        self.failed_trades = 0
        self.last_execution = None
        self.min_profit_threshold = 50
        self.max_position_size = 10
        
    @abstractmethod
    async def initialize(self):
        pass
    
    @abstractmethod
    async def execute(self) -> Optional[Dict]:
        pass
    
    @abstractmethod
    async def cleanup(self):
        pass
    
    def update_metrics(self, result: Dict):
        self.total_trades += 1
        
        if result.get('success'):
            self.successful_trades += 1
            self.total_profit += result.get('profit', 0)
        else:
            self.failed_trades += 1
        
        self.last_execution = datetime.utcnow()
    
    def get_success_rate(self) -> float:
        if self.total_trades == 0:
            return 0
        return self.successful_trades / self.total_trades * 100
    
    def should_execute(self) -> bool:
        if not self.enabled:
            return False
        
        if self.last_execution:
            time_since_last = (datetime.utcnow() - self.last_execution).total_seconds()
            if time_since_last < 1:
                return False
        
        return True
    
    async def validate_opportunity(self, expected_profit: float, required_capital: float) -> bool:
        if expected_profit < self.min_profit_threshold:
            return False
        
        if required_capital > self.max_position_size:
            return False
        
        return True