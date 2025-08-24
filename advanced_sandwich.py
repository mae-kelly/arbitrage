from web3 import Web3
import asyncio
from typing import Dict, List, Tuple
from decimal import Decimal
import struct

class AdvancedSandwichBot:
    
    def __init__(self, w3):
        self.w3 = w3
        
        self.router_signatures = {
            'swapExactTokensForTokens': '0x38ed1739',
            'swapExactETHForTokens': '0x7ff36ab5',
            'swapExactTokensForETH': '0x18cbafe5',
            'swapTokensForExactTokens': '0x8803dbee',
            'swapETHForExactTokens': '0xfb3bdb41',
            'swapTokensForExactETH': '0x4a25d94a',
            'multicall': '0x5ae401dc',
            'exactInputSingle': '0x414bf389',
            'exactInput': '0xc04b8d59',
            'exactOutputSingle': '0xdb3e2198',
            'exactOutput': '0xf28c0498'
        }
        
        self.factory_addresses = {
            'uniswap_v2': '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f',
            'sushiswap': '0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac',
            'uniswap_v3': '0x1F98431c8aD98523631AE4a59f267346ea31F984'
        }
        
        self.cached_pairs = {}
        self.pending_victims = []
        self.daily_sandwich_profit = 0
        
    async def scan_mempool_for_victims(self, pending_txs: List[Dict]) -> List[Dict]:
        victims = []
        
        for tx in pending_txs:
            if not tx.get('to') or not tx.get('input'):
                continue
            
            victim_data = self.parse_victim_transaction(tx)
            
            if victim_data and victim_data['value_usd'] > 10000:
                sandwich_profit = await self.calculate_sandwich_profit(victim_data)
                
                if sandwich_profit > 100:
                    victims.append({
                        'tx': tx,
                        'parsed': victim_data,
                        'expected_profit': sandwich_profit,
                        'front_run_data': self.calculate_optimal_front_run(victim_data, sandwich_profit),
                        'back_run_data': self.calculate_optimal_back_run(victim_data, sandwich_profit)
                    })
        
        return sorted(victims, key=lambda x: x['expected_profit'], reverse=True)
    
    def parse_victim_transaction(self, tx: Dict) -> Dict:
        input_data = tx['input']
        
        if len(input_data) < 10:
            return None
        
        method_id = input_data[:10]
        
        for method_name, signature in self.router_signatures.items():
            if method_id == signature:
                return self.decode_swap_parameters(method_name, input_data, tx)
        
        return None
    
    def decode_swap_parameters(self, method: str, input_data: str, tx: Dict) -> Dict:
        
        try:
            if method == 'swapExactTokensForTokens':
                return self.decode_exact_tokens_for_tokens(input_data, tx)
            elif method == 'swapExactETHForTokens':
                return self.decode_exact_eth_for_tokens(input_data, tx)
            elif method == 'exactInputSingle':
                return self.decode_v3_exact_input_single(input_data, tx)
            elif method == 'multicall':
                return self.decode_multicall(input_data, tx)
            else:
                return self.decode_generic_swap(input_data, tx)
        except:
            return None
    
    def decode_exact_tokens_for_tokens(self, data: str, tx: Dict) -> Dict:
        
        data_bytes = bytes.fromhex(data[10:])
        
        amount_in = int.from_bytes(data_bytes[0:32], 'big')
        amount_out_min = int.from_bytes(data_bytes[32:64], 'big')
        
        path_offset = int.from_bytes(data_bytes[64:96], 'big')
        path_length = int.from_bytes(data_bytes[path_offset:path_offset+32], 'big')
        
        path = []
        for i in range(path_length):
            start = path_offset + 32 + (i * 32)
            address = '0x' + data_bytes[start+12:start+32].hex()
            path.append(Web3.toChecksumAddress(address))
        
        deadline = int.from_bytes(data_bytes[128:160], 'big')
        
        return {
            'method': 'swapExactTokensForTokens',
            'amount_in': amount_in,
            'amount_out_min': amount_out_min,
            'path': path,
            'token_in': path[0],
            'token_out': path[-1],
            'deadline': deadline,
            'value_usd': self.estimate_value_usd(path[0], amount_in),
            'slippage_tolerance': self.calculate_slippage_tolerance(amount_in, amount_out_min, path),
            'pool_address': self.get_pool_address(path[0], path[1])
        }
    
    def decode_v3_exact_input_single(self, data: str, tx: Dict) -> Dict:
        
        data_bytes = bytes.fromhex(data[10:])
        
        struct_data = data_bytes[0:256]
        
        token_in = '0x' + struct_data[12:32].hex()
        token_out = '0x' + struct_data[44:64].hex()
        fee = int.from_bytes(struct_data[64:96], 'big')
        recipient = '0x' + struct_data[108:128].hex()
        deadline = int.from_bytes(struct_data[128:160], 'big')
        amount_in = int.from_bytes(struct_data[160:192], 'big')
        amount_out_min = int.from_bytes(struct_data[192:224], 'big')
        sqrt_price_limit = int.from_bytes(struct_data[224:256], 'big')
        
        pool_address = self.get_v3_pool_address(token_in, token_out, fee)
        
        return {
            'method': 'exactInputSingle',
            'amount_in': amount_in,
            'amount_out_min': amount_out_min,
            'token_in': Web3.toChecksumAddress(token_in),
            'token_out': Web3.toChecksumAddress(token_out),
            'fee': fee,
            'deadline': deadline,
            'sqrt_price_limit': sqrt_price_limit,
            'value_usd': self.estimate_value_usd(token_in, amount_in),
            'pool_address': pool_address,
            'is_v3': True
        }
    
    def decode_multicall(self, data: str, tx: Dict) -> Dict:
        
        data_bytes = bytes.fromhex(data[10:])
        
        deadline = int.from_bytes(data_bytes[0:32], 'big')
        calls_offset = int.from_bytes(data_bytes[32:64], 'big')
        calls_length = int.from_bytes(data_bytes[calls_offset:calls_offset+32], 'big')
        
        decoded_calls = []
        for i in range(calls_length):
            call_offset = int.from_bytes(data_bytes[calls_offset+32+(i*32):calls_offset+64+(i*32)], 'big')
            call_data = data_bytes[calls_offset+call_offset:]
            
            call_length = int.from_bytes(call_data[0:32], 'big')
            actual_call_data = call_data[32:32+call_length]
            
            method_id = '0x' + actual_call_data[:4].hex()
            
            for method_name, sig in self.router_signatures.items():
                if method_id == sig:
                    decoded_calls.append({
                        'method': method_name,
                        'data': '0x' + actual_call_data.hex()
                    })
                    break
        
        return {
            'method': 'multicall',
            'deadline': deadline,
            'calls': decoded_calls,
            'value_usd': tx.get('value', 0) / 10**18 * 3200
        }
    
    def decode_generic_swap(self, data: str, tx: Dict) -> Dict:
        
        return {
            'method': 'unknown',
            'value_usd': tx.get('value', 0) / 10**18 * 3200,
            'raw_data': data
        }
    
    async def calculate_sandwich_profit(self, victim_data: Dict) -> float:
        
        pool_address = victim_data.get('pool_address')
        if not pool_address:
            return 0
        
        reserves = await self.get_pool_reserves(pool_address)
        
        victim_amount_in = victim_data['amount_in']
        
        victim_output = self.calculate_output_amount(
            victim_amount_in,
            reserves[0],
            reserves[1]
        )
        
        price_impact = (victim_amount_in / reserves[0]) ** 0.5
        
        optimal_front_run = victim_amount_in * Decimal('0.3')
        
        front_run_output = self.calculate_output_amount(
            optimal_front_run,
            reserves[0],
            reserves[1]
        )
        
        reserves_after_front = (
            reserves[0] + optimal_front_run,
            reserves[1] - front_run_output
        )
        
        victim_actual_output = self.calculate_output_amount(
            victim_amount_in,
            reserves_after_front[0],
            reserves_after_front[1]
        )
        
        reserves_after_victim = (
            reserves_after_front[0] + victim_amount_in,
            reserves_after_front[1] - victim_actual_output
        )
        
        back_run_output = self.calculate_output_amount(
            front_run_output,
            reserves_after_victim[1],
            reserves_after_victim[0]
        )
        
        gross_profit = float(back_run_output - optimal_front_run)
        
        gas_cost = 300000 * 50 * 10**9 * 3200 / 10**18
        flash_loan_fee = float(optimal_front_run) * 0.0009
        
        net_profit = gross_profit - gas_cost - flash_loan_fee
        
        return max(net_profit, 0)
    
    def calculate_optimal_front_run(self, victim_data: Dict, expected_profit: float) -> Dict:
        
        victim_amount = victim_data['amount_in']
        
        optimal_amount = int(victim_amount * 0.3)
        
        gas_price = self.w3.eth.gas_price
        priority_fee = gas_price + (10 * 10**9)
        
        return {
            'amount': optimal_amount,
            'token_in': victim_data['token_in'],
            'token_out': victim_data['token_out'],
            'gas_price': priority_fee,
            'gas_limit': 200000,
            'pool': victim_data['pool_address']
        }
    
    def calculate_optimal_back_run(self, victim_data: Dict, expected_profit: float) -> Dict:
        
        front_run_output = self.estimate_front_run_output(victim_data)
        
        gas_price = self.w3.eth.gas_price
        priority_fee = gas_price - (1 * 10**9)
        
        return {
            'amount': front_run_output,
            'token_in': victim_data['token_out'],
            'token_out': victim_data['token_in'],
            'gas_price': priority_fee,
            'gas_limit': 200000,
            'pool': victim_data['pool_address']
        }
    
    async def execute_sandwich_attack(self, victim: Dict) -> Dict:
        
        front_run_tx = self.build_front_run_transaction(victim['front_run_data'])
        back_run_tx = self.build_back_run_transaction(victim['back_run_data'])
        
        bundle = [
            front_run_tx,
            victim['tx']['hash'],
            back_run_tx
        ]
        
        result = await self.submit_flashbots_bundle(bundle)
        
        if result['success']:
            self.daily_sandwich_profit += victim['expected_profit']
            return {
                'success': True,
                'profit': victim['expected_profit'],
                'victim_tx': victim['tx']['hash']
            }
        
        return {'success': False, 'reason': result.get('reason')}
    
    def build_front_run_transaction(self, front_run_data: Dict) -> str:
        
        router_address = '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'
        
        swap_data = self.encode_swap(
            front_run_data['token_in'],
            front_run_data['token_out'],
            front_run_data['amount'],
            0,
            [front_run_data['token_in'], front_run_data['token_out']]
        )
        
        tx = {
            'from': self.w3.eth.accounts[0],
            'to': router_address,
            'data': swap_data,
            'gas': front_run_data['gas_limit'],
            'maxFeePerGas': front_run_data['gas_price'],
            'maxPriorityFeePerGas': front_run_data['gas_price'],
            'nonce': self.w3.eth.get_transaction_count(self.w3.eth.accounts[0]),
            'chainId': 1
        }
        
        signed = self.w3.eth.account.sign_transaction(tx, 'PRIVATE_KEY')
        return signed.rawTransaction.hex()
    
    def calculate_output_amount(self, amount_in: int, reserve_in: int, reserve_out: int) -> int:
        amount_in_with_fee = amount_in * 997
        numerator = amount_in_with_fee * reserve_out
        denominator = (reserve_in * 1000) + amount_in_with_fee
        return numerator // denominator
    
    async def get_pool_reserves(self, pool_address: str) -> Tuple[int, int]:
        
        pool = self.w3.eth.contract(
            address=Web3.toChecksumAddress(pool_address),
            abi=[{"name": "getReserves", "type": "function", "outputs": [{"name": "reserve0", "type": "uint112"}, {"name": "reserve1", "type": "uint112"}, {"name": "blockTimestampLast", "type": "uint32"}]}]
        )
        
        reserves = pool.functions.getReserves().call()
        return (reserves[0], reserves[1])
    
    def get_pool_address(self, token0: str, token1: str) -> str:
        
        if token0 > token1:
            token0, token1 = token1, token0
        
        factory = self.factory_addresses['uniswap_v2']
        
        salt = Web3.solidityKeccak(['address', 'address'], [token0, token1])
        init_code_hash = '0x96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f'
        
        pool_address = Web3.solidityKeccak(
            ['bytes1', 'address', 'bytes32', 'bytes32'],
            ['0xff', factory, salt, init_code_hash]
        )[12:]
        
        return Web3.toChecksumAddress('0x' + pool_address.hex())
    
    def estimate_value_usd(self, token: str, amount: int) -> float:
        
        token_prices = {
            '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2': 3200,
            '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48': 1,
            '0xdAC17F958D2ee523a2206206994597C13D831ec7': 1,
            '0x6B175474E89094C44Da98b954EedeAC495271d0F': 1
        }
        
        decimals = {
            '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2': 18,
            '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48': 6,
            '0xdAC17F958D2ee523a2206206994597C13D831ec7': 6,
            '0x6B175474E89094C44Da98b954EedeAC495271d0F': 18
        }
        
        price = token_prices.get(token, 0)
        decimal = decimals.get(token, 18)
        
        return (amount / 10**decimal) * price