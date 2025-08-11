from web3 import Web3
from typing import Dict, List, Optional
import json
import asyncio
from dataclasses import dataclass

@dataclass
class FlashLoanProvider:
    name: str
    contract_address: str
    fee_percentage: float
    max_amount: float
    gas_cost: int

@dataclass
class FlashLoanRequest:
    asset: str
    amount: float
    provider: str
    callback_data: bytes

class FlashLoanManager:
    def __init__(self, web3_provider: str, chain_id: int):
        self.w3 = Web3(Web3.HTTPProvider(web3_provider))
        self.chain_id = chain_id
        self.providers = self._initialize_providers()
        self.arbitrage_contract = None
        
    def _initialize_providers(self) -> Dict[str, FlashLoanProvider]:
        return {
            'aave': FlashLoanProvider(
                name='aave',
                contract_address='0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9',
                fee_percentage=0.05,
                max_amount=1000000,
                gas_cost=250000
            ),
            'compound': FlashLoanProvider(
                name='compound',
                contract_address='0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B',
                fee_percentage=0.02,
                max_amount=500000,
                gas_cost=300000
            ),
            'dydx': FlashLoanProvider(
                name='dydx',
                contract_address='0x1E0447b19BB6EcFdAe1e4AE1694b0C3659614e4e',
                fee_percentage=0.0,
                max_amount=100000,
                gas_cost=400000
            )
        }
    
    def set_arbitrage_contract(self, contract_address: str, abi: List):
        self.arbitrage_contract = self.w3.eth.contract(
            address=contract_address,
            abi=abi
        )
    
    def select_optimal_provider(self, asset: str, amount: float) -> Optional[FlashLoanProvider]:
        suitable_providers = []
        
        for provider in self.providers.values():
            if amount <= provider.max_amount:
                total_cost = (amount * provider.fee_percentage / 100) + \
                           (provider.gas_cost * self._get_gas_price())
                suitable_providers.append((provider, total_cost))
        
        if not suitable_providers:
            return None
            
        return min(suitable_providers, key=lambda x: x[1])[0]
    
    def _get_gas_price(self) -> float:
        try:
            gas_price_wei = self.w3.eth.gas_price
            return self.w3.from_wei(gas_price_wei, 'gwei')
        except:
            return 50.0
    
    async def execute_flash_loan_arbitrage(
        self, 
        asset: str, 
        amount: float,
        arbitrage_params: Dict
    ) -> bool:
        
        provider = self.select_optimal_provider(asset, amount)
        if not provider:
            return False
        
        if not self.arbitrage_contract:
            return False
        
        try:
            asset_address = arbitrage_params['asset_address']
            dex_addresses = arbitrage_params['dex_addresses']
            min_profit = arbitrage_params['min_profit']
            
            encoded_params = self.w3.codec.encode_abi(
                ['address[]', 'uint256', 'uint256'],
                [dex_addresses, int(amount * 1e18), int(min_profit * 1e18)]
            )
            
            if provider.name == 'aave':
                return await self._execute_aave_flash_loan(
                    asset_address, amount, encoded_params
                )
            elif provider.name == 'compound':
                return await self._execute_compound_flash_loan(
                    asset_address, amount, encoded_params
                )
            elif provider.name == 'dydx':
                return await self._execute_dydx_flash_loan(
                    asset_address, amount, encoded_params
                )
                
        except Exception as e:
            print(f"Flash loan execution failed: {e}")
            return False
        
        return False
    
    async def _execute_aave_flash_loan(
        self, 
        asset: str, 
        amount: float, 
        params: bytes
    ) -> bool:
        aave_abi = [
            {
                "inputs": [
                    {"name": "assets", "type": "address[]"},
                    {"name": "amounts", "type": "uint256[]"},
                    {"name": "modes", "type": "uint256[]"},
                    {"name": "onBehalfOf", "type": "address"},
                    {"name": "params", "type": "bytes"},
                    {"name": "referralCode", "type": "uint16"}
                ],
                "name": "flashLoan",
                "type": "function"
            }
        ]
        
        aave_contract = self.w3.eth.contract(
            address=self.providers['aave'].contract_address,
            abi=aave_abi
        )
        
        try:
            tx = aave_contract.functions.flashLoan(
                [asset],
                [int(amount * 1e18)],
                [0],
                self.arbitrage_contract.address,
                params,
                0
            ).build_transaction({
                'from': self.w3.eth.default_account,
                'gas': 2000000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self._get_private_key())
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return receipt.status == 1
            
        except Exception as e:
            print(f"Aave flash loan failed: {e}")
            return False
    
    async def _execute_compound_flash_loan(
        self, 
        asset: str, 
        amount: float, 
        params: bytes
    ) -> bool:
        compound_abi = [
            {
                "inputs": [
                    {"name": "borrower", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "data", "type": "bytes"}
                ],
                "name": "flashLoan",
                "type": "function"
            }
        ]
        
        compound_contract = self.w3.eth.contract(
            address=self.providers['compound'].contract_address,
            abi=compound_abi
        )
        
        try:
            tx = compound_contract.functions.flashLoan(
                self.arbitrage_contract.address,
                int(amount * 1e18),
                params
            ).build_transaction({
                'from': self.w3.eth.default_account,
                'gas': 2000000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self._get_private_key())
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return receipt.status == 1
            
        except Exception as e:
            print(f"Compound flash loan failed: {e}")
            return False
    
    async def _execute_dydx_flash_loan(
        self, 
        asset: str, 
        amount: float, 
        params: bytes
    ) -> bool:
        dydx_abi = [
            {
                "inputs": [
                    {"name": "token", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "data", "type": "bytes"}
                ],
                "name": "initiateFlashLoan",
                "type": "function"
            }
        ]
        
        dydx_contract = self.w3.eth.contract(
            address=self.providers['dydx'].contract_address,
            abi=dydx_abi
        )
        
        try:
            tx = dydx_contract.functions.initiateFlashLoan(
                asset,
                int(amount * 1e18),
                params
            ).build_transaction({
                'from': self.w3.eth.default_account,
                'gas': 2000000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self._get_private_key())
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return receipt.status == 1
            
        except Exception as e:
            print(f"dYdX flash loan failed: {e}")
            return False
    
    def _get_private_key(self) -> str:
        return "0x" + "0" * 64
    
    def calculate_flash_loan_cost(self, provider_name: str, amount: float) -> float:
        if provider_name not in self.providers:
            return float('inf')
            
        provider = self.providers[provider_name]
        fee_cost = amount * provider.fee_percentage / 100
        gas_cost = provider.gas_cost * self._get_gas_price() * 1e-9 * 2000
        
        return fee_cost + gas_cost
