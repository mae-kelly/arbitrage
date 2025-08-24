#!/usr/bin/env python3

import os

new_content = '''
from web3 import Web3
import asyncio
import websockets
import json
from typing import Dict, List
import time
from config_loader import config

class PrivateOrderFlowManager:
    
    def __init__(self):
        self.config = config
        self.w3 = self.config.get_web3_instance()
        
        # Load mempool sources from config
        self.mempool_sources = self.load_mempool_sources()
        
        # Load MEV relays from public registry
        self.mev_relays = self.load_mev_relays()
        
        self.active_connections = {}
        self.order_queue = asyncio.Queue()
        
    def load_mempool_sources(self) -> Dict:
        """Load mempool sources from configuration"""
        sources = {}
        
        # BloXroute
        if self.config.config['api_keys'].get('bloxroute'):
            sources['bloxroute'] = {
                'endpoint': 'wss://api.bloxroute.com/ws',
                'api_key': self.config.config['api_keys']['bloxroute'],
                'authenticated': True
            }
        
        # Blocknative
        if self.config.config['api_keys'].get('blocknative'):
            sources['blocknative'] = {
                'endpoint': 'wss://api.blocknative.com/v0',
                'api_key': self.config.config['api_keys']['blocknative'],
                'authenticated': True
            }
        
        # Public mempool (limited)
        sources['public'] = {
            'endpoint': None,  # Will use Web3 filters
            'authenticated': False
        }
        
        return sources
    
    def load_mev_relays(self) -> Dict:
        """Load MEV relay information from public sources"""
        # These are public endpoints
        relays = {
            'flashbots': {
                'endpoint': 'https://relay.flashbots.net',
                'builder_api': 'https://relay.flashbots.net'
            },
            'bloxroute': {
                'endpoint': 'https://bloxroute.max-profit.blxrbdn.com',
                'builder_api': 'https://bloxroute.max-profit.blxrbdn.com'
            },
            'blocknative': {
                'endpoint': 'https://api.blocknative.com/v1/auction',
                'builder_api': 'https://api.blocknative.com/v1/auction'
            },
            'eden': {
                'endpoint': 'https://api.edennetwork.io/v1/relay',
                'builder_api': 'https://api.edennetwork.io/v1/relay'
            }
        }
        
        return relays
    
    async def connect_mempool_source(self, name: str, source: Dict):
        """Connect to a mempool source"""
        if not source.get('authenticated'):
            # Use Web3 pending transaction filter
            return await self.setup_web3_mempool_monitor()
        
        try:
            # Connect to authenticated WebSocket
            headers = {
                'Authorization': source['api_key']
            }
            
            async with websockets.connect(
                source['endpoint'],
                extra_headers=headers
            ) as websocket:
                self.active_connections[name] = websocket
                
                # Subscribe to mempool
                await self.subscribe_to_mempool(websocket, name)
                
                # Handle messages
                await self.handle_mempool_messages(websocket, name)
                
        except Exception as e:
            print(f"Failed to connect to {name}: {e}")
    
    async def setup_web3_mempool_monitor(self):
        """Monitor mempool using Web3 filters"""
        pending_filter = self.w3.eth.filter('pending')
        
        while True:
            try:
                pending_txs = pending_filter.get_new_entries()
                
                for tx_hash in pending_txs:
                    try:
                        tx = self.w3.eth.get_transaction(tx_hash)
                        if tx:
                            await self.process_transaction(tx)
                    except:
                        continue
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                await asyncio.sleep(1)
    
    async def process_transaction(self, tx: Dict):
        """Process a mempool transaction"""
        # Check if transaction is interesting
        if self.is_interesting_transaction(tx):
            await self.order_queue.put({
                'source': 'mempool',
                'transaction': tx,
                'timestamp': time.time()
            })
    
    def is_interesting_transaction(self, tx: Dict) -> bool:
        """Determine if transaction is worth processing"""
        # Large value transfers
        if tx.get('value', 0) > 10 * 10**18:
            return True
        
        # DEX routers
        dex_routers = self.config.config.get('contracts', {})
        if tx.get('to') in dex_routers.values():
            return True
        
        # High gas price (potential MEV)
        if tx.get('gasPrice', 0) > self.w3.eth.gas_price * 2:
            return True
        
        return False
    
    async def submit_bundle(self, bundle: List[Dict]) -> Dict:
        """Submit bundle to MEV relays"""
        results = []
        
        for relay_name, relay_config in self.mev_relays.items():
            try:
                result = await self.submit_to_relay(
                    relay_config['endpoint'],
                    bundle
                )
                results.append({
                    'relay': relay_name,
                    'success': result.get('success', False),
                    'response': result
                })
            except Exception as e:
                results.append({
                    'relay': relay_name,
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'results': results,
            'accepted': any(r['success'] for r in results)
        }
    
    async def submit_to_relay(self, endpoint: str, bundle: List[Dict]) -> Dict:
        """Submit bundle to specific relay"""
        import aiohttp
        
        payload = {
            'jsonrpc': '2.0',
            'method': 'eth_sendBundle',
            'params': [{
                'txs': bundle,
                'blockNumber': hex(self.w3.eth.block_number + 1)
            }],
            'id': 1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=payload) as response:
                return await response.json()
'''

with open('private_order_flow.py', 'w') as f:
    f.write(new_content)

print("✅ Fixed private_order_flow.py with dynamic configuration")
