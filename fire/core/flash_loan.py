# core/flash_loan.py

import json
from typing import Dict, Optional
from web3 import Web3
from eth_account import Account
from config import Config

class FlashLoanExecutor:
    def __init__(self, rpc_manager, dex_client):
        self.config = Config()
        self.rpc = rpc_manager
        self.dex = dex_client
        self.account = Account.from_key(self.config.PRIVATE_KEY)
        
        with open('abi/flashloan_arbitrage.json', 'r') as f:
            self.contract_abi = json.load(f)
        
        self.contract = None
        
    async def initialize(self):
        self.w3 = self.rpc.get_w3()
        
        if self.config.FLASHLOAN_CONTRACT_ADDRESS:
            self.contract = self.w3.eth.contract(
                address=self.config.FLASHLOAN_CONTRACT_ADDRESS,
                abi=self.contract_abi
            )
    
    async def execute_arbitrage(self, token: str, amount: int, target_dex: str, 
                               min_profit: int, strategy_params: bytes) -> Dict:
        
        if not self.contract:
            raise Exception("Flash loan contract not deployed")
        
        params = self.w3.codec.encode_abi(
            ['address', 'uint256', 'bytes'],
            [target_dex, min_profit, strategy_params]
        )
        
        tx = self.contract.functions.requestFlashLoan(
            token,
            amount,
            params
        ).build_transaction({
            'from': self.config.WALLET_ADDRESS,
            'gas': 2000000,
            'gasPrice': await self.rpc.get_gas_price(),
            'nonce': self.w3.eth.get_transaction_count(self.config.WALLET_ADDRESS)
        })
        
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = await self.rpc.send_transaction(signed_tx.rawTransaction)
        
        receipt = await self.rpc.wait_for_transaction(tx_hash)
        
        if receipt['status'] == 1:
            profit = self.parse_profit_from_logs(receipt['logs'])
            return {
                'success': True,
                'tx_hash': tx_hash.hex(),
                'profit': profit,
                'gas_used': receipt['gasUsed'],
                'gas_price': receipt['effectiveGasPrice']
            }
        else:
            return {
                'success': False,
                'tx_hash': tx_hash.hex(),
                'profit': 0,
                'gas_used': receipt['gasUsed'],
                'gas_price': receipt['effectiveGasPrice']
            }
    
    def parse_profit_from_logs(self, logs: list) -> float:
        for log in logs:
            if log['topics'][0] == self.w3.keccak(text='ProfitMade(uint256)'):
                profit_wei = int(log['data'], 16)
                return Web3.from_wei(profit_wei, 'ether')
        return 0
    
    async def calculate_flash_loan_fee(self, protocol: str, amount: int) -> int:
        if protocol == 'aave':
            return amount * 5 // 10000
        elif protocol == 'dydx':
            return 0
        elif protocol == 'uniswap':
            return amount * 30 // 10000
        else:
            return amount * 9 // 10000
    
    async def get_max_flash_loan_amount(self, token: str, protocol: str) -> int:
        if protocol == 'aave':
            pool_address = '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'
            
            with open('abi/aave_pool.json', 'r') as f:
                pool_abi = json.load(f)
            
            pool = self.w3.eth.contract(address=pool_address, abi=pool_abi)
            
            reserve_data = pool.functions.getReserveData(token).call()
            
            total_liquidity = reserve_data[0]
            return int(total_liquidity * 0.9)
            
        elif protocol == 'dydx':
            solo_margin_address = '0x1E0447b19BB6EcFdAe1e4AE1694b0C3659614e4e'
            
            with open('abi/dydx_solo.json', 'r') as f:
                solo_abi = json.load(f)
            
            solo = self.w3.eth.contract(address=solo_margin_address, abi=solo_abi)
            
            market_id = self.get_dydx_market_id(token)
            if market_id is None:
                return 0
            
            market_info = solo.functions.getMarketTotalPar(market_id).call()
            return market_info[0]
            
        else:
            return 0
    
    def get_dydx_market_id(self, token: str) -> Optional[int]:
        markets = {
            self.config.TOKENS['WETH']: 0,
            self.config.TOKENS['USDC']: 2,
            self.config.TOKENS['DAI']: 3
        }
        
        return markets.get(token)
    
    async def simulate_flash_loan(self, token: str, amount: int, strategy_params: Dict) -> Dict:
        fee = await self.calculate_flash_loan_fee('aave', amount)
        
        simulated_profit = strategy_params.get('expected_profit', 0)
        
        if simulated_profit > fee:
            return {
                'profitable': True,
                'expected_profit': simulated_profit - fee,
                'flash_loan_fee': fee,
                'total_amount_needed': amount + fee
            }
        else:
            return {
                'profitable': False,
                'expected_profit': simulated_profit - fee,
                'flash_loan_fee': fee,
                'total_amount_needed': amount + fee
            }