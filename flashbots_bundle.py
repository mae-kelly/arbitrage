from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount
import aiohttp
import json
from typing import List, Dict
import time

class FlashbotsClient:
    def __init__(self, w3: Web3, account: LocalAccount):
        self.w3 = w3
        self.account = account
        self.flashbots_url = "https://relay.flashbots.net"
        self.builder_urls = [
            "https://relay.flashbots.net",
            "https://builder0x69.io",
            "https://rsync-builder.xyz",
            "https://relay.ultrasound.money"
        ]
        
        self.reputation_score = 0.5
        self.successful_bundles = 0
        self.total_bundles = 0
    
    async def send_bundle(self, transactions: List[str]) -> Dict:
        bundle = self.construct_bundle(transactions)
        
        signed_bundle = self.sign_bundle(bundle)
        
        results = await self.send_to_all_builders(signed_bundle)
        
        best_result = self.select_best_result(results)
        
        self.total_bundles += 1
        if best_result.get('bundleHash'):
            self.successful_bundles += 1
            self.update_reputation()
        
        return best_result
    
    def construct_bundle(self, transactions: List[str]) -> Dict:
        current_block = self.w3.eth.block_number
        
        return {
            "jsonrpc": "2.0",
            "method": "eth_sendBundle",
            "params": [{
                "txs": transactions,
                "blockNumber": hex(current_block + 1),
                "minTimestamp": 0,
                "maxTimestamp": int(time.time()) + 120,
                "revertingTxHashes": []
            }],
            "id": 1
        }
    
    def sign_bundle(self, bundle: Dict) -> Dict:
        body = json.dumps(bundle)
        
        signature = self.account.signHash(
            Web3.keccak(text=body)
        )
        
        bundle['signature'] = signature.signature.hex()
        
        return bundle
    
    async def send_to_all_builders(self, bundle: Dict) -> List[Dict]:
        results = []
        
        async with aiohttp.ClientSession() as session:
            for builder_url in self.builder_urls:
                try:
                    headers = {
                        'Content-Type': 'application/json',
                        'X-Flashbots-Signature': f"{self.account.address}:{bundle['signature']}"
                    }
                    
                    async with session.post(
                        builder_url,
                        json=bundle,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        result = await response.json()
                        result['builder'] = builder_url
                        results.append(result)
                        
                except Exception:
                    continue
        
        return results
    
    def select_best_result(self, results: List[Dict]) -> Dict:
        valid_results = [r for r in results if 'result' in r]
        
        if not valid_results:
            return {'error': 'No valid responses from builders'}
        
        return valid_results[0]
    
    async def get_bundle_status(self, bundle_hash: str) -> Dict:
        async with aiohttp.ClientSession() as session:
            params = {
                "jsonrpc": "2.0",
                "method": "flashbots_getBundleStats",
                "params": [{
                    "bundleHash": bundle_hash,
                    "blockNumber": hex(self.w3.eth.block_number)
                }],
                "id": 1
            }
            
            headers = {
                'Content-Type': 'application/json',
                'X-Flashbots-Signature': self.create_signature(json.dumps(params))
            }
            
            async with session.post(
                self.flashbots_url,
                json=params,
                headers=headers
            ) as response:
                result = await response.json()
                
                if 'result' in result and result['result']:
                    stats = result['result']
                    if stats.get('isSimulated'):
                        return {
                            'status': 'included' if stats.get('isSentToMiners') else 'pending',
                            'receipt': stats
                        }
                
                return {'status': 'pending'}
    
    def create_signature(self, body: str) -> str:
        signature = self.account.signHash(
            Web3.keccak(text=body)
        )
        return f"{self.account.address}:{signature.signature.hex()}"
    
    def update_reputation(self):
        self.reputation_score = self.successful_bundles / max(self.total_bundles, 1)
    
    async def send_private_transaction(self, tx: Dict) -> str:
        params = {
            "jsonrpc": "2.0",
            "method": "eth_sendPrivateTransaction",
            "params": [{
                "tx": tx,
                "maxBlockNumber": hex(self.w3.eth.block_number + 25),
                "preferences": {
                    "fast": True,
                    "privacy": {
                        "hints": ["calldata", "logs", "default_logs"],
                        "builders": self.builder_urls
                    }
                }
            }],
            "id": 1
        }
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'Content-Type': 'application/json',
                'X-Flashbots-Signature': self.create_signature(json.dumps(params))
            }
            
            async with session.post(
                self.flashbots_url,
                json=params,
                headers=headers
            ) as response:
                result = await response.json()
                return result.get('result', {}).get('txHash')
    
    def calculate_priority_fee(self, target_position: int = 1) -> int:
        base_fee = self.w3.eth.get_block('latest')['baseFeePerGas']
        
        if target_position == 1:
            priority_fee = 10 * 10**9
        elif target_position <= 5:
            priority_fee = 5 * 10**9
        else:
            priority_fee = 2 * 10**9
        
        return base_fee + priority_fee