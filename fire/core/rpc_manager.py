# core/rpc_manager.py

import asyncio
import time
from typing import List, Dict, Any, Optional
from web3 import Web3
from web3.providers import HTTPProvider
import aiohttp
from config import Config

class RPCProvider:
    def __init__(self, name: str, url: str, weight: int = 1):
        self.name = name
        self.url = url
        self.weight = weight
        self.is_healthy = True
        self.response_times = []
        self.error_count = 0
        self.last_check = time.time()
        self.w3 = Web3(HTTPProvider(url))

class RPCManager:
    def __init__(self):
        self.config = Config()
        self.providers = []
        self.current_provider_index = 0
        self.health_check_interval = 30
        
    async def initialize(self):
        self.providers = [
            RPCProvider("alchemy_main", f"https://eth-mainnet.g.alchemy.com/v2/{self.config.ALCHEMY_API_KEY}", 2),
            RPCProvider("infura_main", f"https://mainnet.infura.io/v3/{self.config.INFURA_API_KEY}", 1),
        ]
        
        await self.health_check_all()
        asyncio.create_task(self.periodic_health_check())
    
    async def health_check_all(self):
        tasks = [self.check_provider_health(provider) for provider in self.providers]
        await asyncio.gather(*tasks)
    
    async def check_provider_health(self, provider: RPCProvider):
        try:
            start_time = time.time()
            block_number = provider.w3.eth.block_number
            response_time = time.time() - start_time
            
            provider.response_times.append(response_time)
            if len(provider.response_times) > 100:
                provider.response_times.pop(0)
            
            provider.is_healthy = True
            provider.error_count = 0
            provider.last_check = time.time()
            
            return True
            
        except Exception as e:
            provider.error_count += 1
            if provider.error_count >= 3:
                provider.is_healthy = False
            return False
    
    async def periodic_health_check(self):
        while True:
            await asyncio.sleep(self.health_check_interval)
            await self.health_check_all()
    
    def get_best_provider(self) -> Optional[RPCProvider]:
        healthy_providers = [p for p in self.providers if p.is_healthy]
        
        if not healthy_providers:
            return None
        
        sorted_providers = sorted(healthy_providers, 
                                 key=lambda p: (sum(p.response_times[-10:]) / len(p.response_times[-10:]) if p.response_times else float('inf')))
        
        return sorted_providers[0]
    
    async def make_request(self, method: str, params: list = None) -> Any:
        provider = self.get_best_provider()
        
        if not provider:
            await self.health_check_all()
            provider = self.get_best_provider()
            if not provider:
                raise Exception("All RPC providers are unavailable")
        
        try:
            if method == 'eth_call':
                result = provider.w3.eth.call(params[0], params[1] if len(params) > 1 else 'latest')
            elif method == 'eth_getTransactionReceipt':
                result = provider.w3.eth.get_transaction_receipt(params[0])
            elif method == 'eth_sendRawTransaction':
                result = provider.w3.eth.send_raw_transaction(params[0])
            elif method == 'eth_gasPrice':
                result = provider.w3.eth.gas_price
            elif method == 'eth_blockNumber':
                result = provider.w3.eth.block_number
            elif method == 'eth_getBalance':
                result = provider.w3.eth.get_balance(params[0])
            else:
                result = provider.w3.provider.make_request(method, params)
            
            return result
            
        except Exception as e:
            provider.error_count += 1
            if provider.error_count >= 3:
                provider.is_healthy = False
            
            for backup_provider in self.providers:
                if backup_provider != provider and backup_provider.is_healthy:
                    try:
                        return await self.make_request_with_provider(backup_provider, method, params)
                    except:
                        continue
            
            raise e
    
    async def make_request_with_provider(self, provider: RPCProvider, method: str, params: list = None) -> Any:
        if method == 'eth_call':
            return provider.w3.eth.call(params[0], params[1] if len(params) > 1 else 'latest')
        elif method == 'eth_sendRawTransaction':
            return provider.w3.eth.send_raw_transaction(params[0])
        else:
            return provider.w3.provider.make_request(method, params)
    
    def get_w3(self) -> Web3:
        provider = self.get_best_provider()
        if provider:
            return provider.w3
        raise Exception("No healthy RPC provider available")
    
    async def get_gas_price(self) -> int:
        return await self.make_request('eth_gasPrice')
    
    async def get_block_number(self) -> int:
        return await self.make_request('eth_blockNumber')
    
    async def send_transaction(self, signed_tx: bytes) -> str:
        return await self.make_request('eth_sendRawTransaction', [signed_tx])
    
    async def wait_for_transaction(self, tx_hash: str, timeout: int = 120) -> dict:
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                receipt = await self.make_request('eth_getTransactionReceipt', [tx_hash])
                if receipt:
                    return receipt
            except:
                pass
            
            await asyncio.sleep(1)
        
        raise TimeoutError(f"Transaction {tx_hash} not mined after {timeout} seconds")