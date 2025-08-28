# core/dex_client.py

import json
from typing import Dict, List, Optional
from web3 import Web3
from eth_account import Account
from config import Config

class DEXClient:
    def __init__(self, rpc_manager):
        self.config = Config()
        self.rpc = rpc_manager
        self.account = Account.from_key(self.config.PRIVATE_KEY)
        self.total_gas_spent = 0
        
        with open('abi/uniswap_v3_router.json', 'r') as f:
            self.uniswap_router_abi = json.load(f)
        
        with open('abi/erc20.json', 'r') as f:
            self.erc20_abi = json.load(f)
    
    async def initialize(self):
        self.w3 = self.rpc.get_w3()
        
        self.uniswap_router = self.w3.eth.contract(
            address=self.config.DEX_ADDRESSES['uniswap_v3_router'],
            abi=self.uniswap_router_abi
        )
    
    async def get_wallet_balance(self) -> Dict[str, float]:
        balances = {}
        
        eth_balance = await self.rpc.make_request('eth_getBalance', [self.config.WALLET_ADDRESS])
        balances['ETH'] = float(Web3.from_wei(eth_balance, 'ether'))
        
        for token_symbol, token_address in self.config.TOKENS.items():
            if token_symbol != 'WETH':
                contract = self.w3.eth.contract(address=token_address, abi=self.erc20_abi)
                balance = contract.functions.balanceOf(self.config.WALLET_ADDRESS).call()
                decimals = contract.functions.decimals().call()
                balances[token_symbol] = balance / (10 ** decimals)
        
        return balances
    
    async def approve_token(self, token_address: str, spender: str, amount: int) -> str:
        token_contract = self.w3.eth.contract(address=token_address, abi=self.erc20_abi)
        
        current_allowance = token_contract.functions.allowance(
            self.config.WALLET_ADDRESS, 
            spender
        ).call()
        
        if current_allowance >= amount:
            return None
        
        tx = token_contract.functions.approve(spender, amount).build_transaction({
            'from': self.config.WALLET_ADDRESS,
            'gas': 100000,
            'gasPrice': await self.rpc.get_gas_price(),
            'nonce': self.w3.eth.get_transaction_count(self.config.WALLET_ADDRESS)
        })
        
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = await self.rpc.send_transaction(signed_tx.rawTransaction)
        
        receipt = await self.rpc.wait_for_transaction(tx_hash)
        self.total_gas_spent += receipt['gasUsed'] * receipt['effectiveGasPrice']
        
        return tx_hash
    
    async def swap_exact_input_single(self, token_in: str, token_out: str, amount_in: int, 
                                      amount_out_minimum: int, pool_fee: int = 3000) -> str:
        
        await self.approve_token(token_in, self.config.DEX_ADDRESSES['uniswap_v3_router'], amount_in)
        
        params = {
            'tokenIn': token_in,
            'tokenOut': token_out,
            'fee': pool_fee,
            'recipient': self.config.WALLET_ADDRESS,
            'deadline': self.w3.eth.get_block('latest')['timestamp'] + 1200,
            'amountIn': amount_in,
            'amountOutMinimum': amount_out_minimum,
            'sqrtPriceLimitX96': 0
        }
        
        tx = self.uniswap_router.functions.exactInputSingle(params).build_transaction({
            'from': self.config.WALLET_ADDRESS,
            'gas': 250000,
            'gasPrice': await self.rpc.get_gas_price(),
            'nonce': self.w3.eth.get_transaction_count(self.config.WALLET_ADDRESS),
            'value': amount_in if token_in == self.config.TOKENS['WETH'] else 0
        })
        
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = await self.rpc.send_transaction(signed_tx.rawTransaction)
        
        receipt = await self.rpc.wait_for_transaction(tx_hash)
        self.total_gas_spent += receipt['gasUsed'] * receipt['effectiveGasPrice']
        
        return tx_hash
    
    async def get_pool_price(self, token_a: str, token_b: str, pool_fee: int = 3000) -> float:
        factory_address = '0x1F98431c8aD98523631AE4a59f267346ea31F984'
        
        with open('abi/uniswap_v3_factory.json', 'r') as f:
            factory_abi = json.load(f)
        
        factory = self.w3.eth.contract(address=factory_address, abi=factory_abi)
        
        pool_address = factory.functions.getPool(token_a, token_b, pool_fee).call()
        
        if pool_address == '0x0000000000000000000000000000000000000000':
            return 0
        
        with open('abi/uniswap_v3_pool.json', 'r') as f:
            pool_abi = json.load(f)
        
        pool = self.w3.eth.contract(address=pool_address, abi=pool_abi)
        
        slot0 = pool.functions.slot0().call()
        sqrt_price_x96 = slot0[0]
        
        price = (sqrt_price_x96 / 2**96) ** 2
        
        token0 = pool.functions.token0().call()
        if token0.lower() != token_a.lower():
            price = 1 / price
        
        return price
    
    async def get_reserves_uniswap_v2(self, token_a: str, token_b: str) -> tuple:
        factory_address = '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f'
        
        with open('abi/uniswap_v2_factory.json', 'r') as f:
            factory_abi = json.load(f)
        
        factory = self.w3.eth.contract(address=factory_address, abi=factory_abi)
        
        pair_address = factory.functions.getPair(token_a, token_b).call()
        
        if pair_address == '0x0000000000000000000000000000000000000000':
            return (0, 0)
        
        with open('abi/uniswap_v2_pair.json', 'r') as f:
            pair_abi = json.load(f)
        
        pair = self.w3.eth.contract(address=pair_address, abi=pair_abi)
        
        reserves = pair.functions.getReserves().call()
        token0 = pair.functions.token0().call()
        
        if token0.lower() == token_a.lower():
            return (reserves[0], reserves[1])
        else:
            return (reserves[1], reserves[0])
    
    async def estimate_gas(self, transaction: dict) -> int:
        try:
            return self.w3.eth.estimate_gas(transaction)
        except Exception as e:
            return 300000
    
    async def get_gas_price_wei(self) -> int:
        return await self.rpc.get_gas_price()
    
    async def get_total_gas_spent(self) -> float:
        return Web3.from_wei(self.total_gas_spent, 'ether')
    
    async def cleanup(self):
        pass
    
    async def execute_multicall(self, calls: List[tuple]) -> List:
        multicall_address = self.config.MULTICALL_CONTRACT_ADDRESS
        
        with open('abi/multicall3.json', 'r') as f:
            multicall_abi = json.load(f)
        
        multicall = self.w3.eth.contract(address=multicall_address, abi=multicall_abi)
        
        encoded_calls = []
        for target, function_data in calls:
            encoded_calls.append({
                'target': target,
                'allowFailure': True,
                'callData': function_data
            })
        
        results = multicall.functions.tryAggregate(False, encoded_calls).call()
        
        return results