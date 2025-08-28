# utils/security_manager.py

import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from config import Config

class SecurityManager:
    def __init__(self):
        self.config = Config()
        self.daily_loss_limit = 0.03
        self.max_drawdown = 0.20
        self.position_limit = 0.02
        self.circuit_breaker_active = False
        self.daily_losses = {}
        self.peak_balance = 0
        self.current_balance = 0
        self.failed_tx_count = 0
        self.max_failed_tx = 10
        
    def check_position_limits(self, position_size: float, total_capital: float) -> bool:
        if position_size > total_capital * self.position_limit:
            return False
        
        if position_size > self.config.MAX_POSITION_SIZE_ETH:
            return False
        
        return True
    
    def check_daily_loss_limit(self, loss: float, total_capital: float) -> bool:
        today = datetime.utcnow().date()
        
        if today not in self.daily_losses:
            self.daily_losses[today] = 0
        
        self.daily_losses[today] += loss
        
        if self.daily_losses[today] > total_capital * self.daily_loss_limit:
            self.activate_circuit_breaker()
            return False
        
        return True
    
    def check_max_drawdown(self, current_balance: float) -> bool:
        self.current_balance = current_balance
        
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        if self.peak_balance > 0:
            drawdown = (self.peak_balance - current_balance) / self.peak_balance
            
            if drawdown > self.max_drawdown:
                self.activate_circuit_breaker()
                return False
        
        return True
    
    def activate_circuit_breaker(self):
        self.circuit_breaker_active = True
        self.circuit_breaker_activated_at = datetime.utcnow()
    
    def deactivate_circuit_breaker(self):
        self.circuit_breaker_active = False
        self.circuit_breaker_activated_at = None
    
    def is_circuit_breaker_active(self) -> bool:
        if self.circuit_breaker_active:
            if hasattr(self, 'circuit_breaker_activated_at'):
                time_since_activation = (datetime.utcnow() - self.circuit_breaker_activated_at).total_seconds()
                
                if time_since_activation > 3600:
                    self.deactivate_circuit_breaker()
                    return False
            
            return True
        
        return False
    
    def check_strategy_health(self, strategy) -> bool:
        if self.is_circuit_breaker_active():
            return False
        
        if hasattr(strategy, 'failed_trades') and strategy.failed_trades > 10:
            return False
        
        if hasattr(strategy, 'get_success_rate'):
            if strategy.total_trades > 20 and strategy.get_success_rate() < 30:
                return False
        
        return True
    
    def validate_transaction(self, tx_params: Dict) -> bool:
        if 'gas' in tx_params and tx_params['gas'] > 5000000:
            return False
        
        if 'gasPrice' in tx_params:
            max_gas_wei = self.config.MAX_GAS_PRICE_GWEI * 10**9
            if tx_params['gasPrice'] > max_gas_wei:
                return False
        
        if 'value' in tx_params:
            max_value_wei = self.config.MAX_POSITION_SIZE_ETH * 10**18
            if tx_params['value'] > max_value_wei:
                return False
        
        return True
    
    def record_failed_transaction(self):
        self.failed_tx_count += 1
        
        if self.failed_tx_count >= self.max_failed_tx:
            self.activate_circuit_breaker()
    
    def reset_daily_counters(self):
        yesterday = (datetime.utcnow() - timedelta(days=1)).date()
        
        if yesterday in self.daily_losses:
            del self.daily_losses[yesterday]
        
        self.failed_tx_count = 0
    
    def get_risk_metrics(self) -> Dict:
        current_drawdown = 0
        if self.peak_balance > 0:
            current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
        
        return {
            'circuit_breaker_active': self.circuit_breaker_active,
            'daily_loss': self.daily_losses.get(datetime.utcnow().date(), 0),
            'current_drawdown': current_drawdown,
            'failed_transactions': self.failed_tx_count,
            'peak_balance': self.peak_balance,
            'current_balance': self.current_balance
        }
    
    def validate_api_response(self, response: Dict) -> bool:
        if not response:
            return False
        
        if 'error' in response or 'errors' in response:
            return False
        
        if 'code' in response and response['code'] != '0' and response['code'] != 0:
            return False
        
        return True
    
    def sanitize_input(self, input_data: str) -> str:
        dangerous_chars = ['<', '>', '"', "'", '&', '\n', '\r', '\t']
        
        sanitized = input_data
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized[:1000]