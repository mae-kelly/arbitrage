import asyncio
import json
from web3 import Web3
from web3.middleware import geth_poa_middleware
from typing import Dict, List, Any, Optional
import redis.asyncio as redis
from loguru import logger
from src.config import settings, DEX_CONFIGS

class Web3Connector:
   def __init__(self):
       self.w3_instances = {}
       self.redis_client = None
       self.pool_contracts = {}
       self.factory_contracts = {}
       
   async def initialize(self):
       self.redis_client = redis.Redis(
           host=settings.redis_host,
           port=settings.redis_port,
           db=settings.redis_db,
           decode_responses=True
       )
       
       for chain_id, config in DEX_CONFIGS.items():
           await self._setup_chain(chain_id, config)
   
   async def _setup_chain(self, chain_id: str, config: Dict):
       for rpc_url in config['rpc_urls']:
           try:
               w3 = Web3(Web3.HTTPProvider(rpc_url))
               if chain_id in ['bsc', 'polygon']:
                   w3.middleware_onion.inject(geth_poa_middleware, layer=0)
               
               if w3.is_connected():
                   self.w3_instances[chain_id] = w3
                   logger.info(f"Connected to {chain_id} via {rpc_url}")
                   break
           except Exception as e:
               logger.warning(f"Failed to connect to {chain_id} via {rpc_url}: {e}")
       
       if chain_id in self.w3_instances:
           await self._load_dex_contracts(chain_id, config['dexes'])
   
   async def _load_dex_contracts(self, chain_id: str, dexes: Dict):
       w3 = self.w3_instances[chain_id]
       
       uniswap_v2_abi = [
           {
               "inputs": [{"internalType": "address", "name": "", "type": "address"}, {"internalType": "address", "name": "", "type": "address"}],
               "name": "getPair",
               "outputs": [{"internalType": "address", "name": "", "type": "address"}],
               "stateMutability": "view",
               "type": "function"
           }
       ]
       
       pair_abi = [
           {
               "inputs": [],
               "name": "getReserves",
               "outputs": [{"internalType": "uint112", "name": "_reserve0", "type": "uint112"}, {"internalType": "uint112", "name": "_reserve1", "type": "uint112"}, {"internalType": "uint32", "name": "_blockTimestampLast", "type": "uint32"}],
               "stateMutability": "view",
               "type": "function"
           },
           {
               "inputs": [],
               "name": "token0",
               "outputs": [{"internalType": "address", "name": "", "type": "address"}],
               "stateMutability": "view",
               "type": "function"
           },
           {
               "inputs": [],
               "name": "token1",
               "outputs": [{"internalType": "address", "name": "", "type": "address"}],
               "stateMutability": "view",
               "type": "function"
           }
       ]
       
       for dex_name, factory_address in dexes.items():
           try:
               contract = w3.eth.contract(address=factory_address, abi=uniswap_v2_abi)
               if chain_id not in self.factory_contracts:
                   self.factory_contracts[chain_id] = {}
               self.factory_contracts[chain_id][dex_name] = {
                   'contract': contract,
                   'pair_abi': pair_abi
               }
           except Exception as e:
               logger.error(f"Failed to load {dex_name} on {chain_id}: {e}")
   
   async def get_pair_reserves(self, chain_id: str, dex_name: str, token0: str, token1: str) -> Optional[Dict]:
       if chain_id not in self.factory_contracts or dex_name not in self.factory_contracts[chain_id]:
           return None
       
       try:
           factory = self.factory_contracts[chain_id][dex_name]['contract']
           pair_abi = self.factory_contracts[chain_id][dex_name]['pair_abi']
           w3 = self.w3_instances[chain_id]
           
           pair_address = factory.functions.getPair(token0, token1).call()
           if pair_address == '0x0000000000000000000000000000000000000000':
               return None
           
           pair_contract = w3.eth.contract(address=pair_address, abi=pair_abi)
           reserves = pair_contract.functions.getReserves().call()
           token0_addr = pair_contract.functions.token0().call()
           token1_addr = pair_contract.functions.token1().call()
           
           return {
               'pair_address': pair_address,
               'reserve0': reserves[0],
               'reserve1': reserves[1],
               'token0': token0_addr,
               'token1': token1_addr,
               'timestamp': reserves[2]
           }
       except Exception as e:
           logger.error(f"Error getting reserves for {token0}/{token1} on {dex_name}: {e}")
           return None
   
   async def calculate_dex_price(self, chain_id: str, dex_name: str, token0: str, token1: str, amount_in: int) -> Optional[int]:
       reserves = await self.get_pair_reserves(chain_id, dex_name, token0, token1)
       if not reserves:
           return None
       
       reserve_in = reserves['reserve0'] if reserves['token0'].lower() == token0.lower() else reserves['reserve1']
       reserve_out = reserves['reserve1'] if reserves['token0'].lower() == token0.lower() else reserves['reserve0']
       
       amount_in_with_fee = amount_in * 997
       numerator = amount_in_with_fee * reserve_out
       denominator = reserve_in * 1000 + amount_in_with_fee
       
       return numerator // denominator
   
   async def monitor_pools(self, token_pairs: List[tuple]):
       while True:
           for chain_id in self.w3_instances.keys():
               for dex_name in self.factory_contracts.get(chain_id, {}):
                   for token0, token1 in token_pairs:
                       reserves = await self.get_pair_reserves(chain_id, dex_name, token0, token1)
                       if reserves:
                           key = f"dex_reserves:{chain_id}:{dex_name}:{token0}:{token1}"
                           await self.redis_client.set(key, json.dumps(reserves), ex=30)
           
           await asyncio.sleep(10)
   
   async def close(self):
       if self.redis_client:
           await self.redis_client.close()
