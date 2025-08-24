from blockchain_queries import blockchain
from config_loader import config
from contract_registry import ContractRegistry
from web3 import Web3
from typing import List, Dict
import json

class FlashLoanAggregator:
    
    async def get_real_protocol_limits(self):
        """Get real-time liquidity from protocols"""
        limits = {}
        
        # Aave V3 - Query actual reserves
        for token_symbol, token_address in self.token_addresses.items():
            try:
                aave_pool = self.w3.eth.contract(
                    address=self.protocols['aave_v3']['address'],
                    abi=[{"inputs":[{"name":"asset","type":"address"}],"name":"getReserveData","outputs":[{"components":[{"name":"configuration","type":"uint256"},{"name":"liquidityIndex","type":"uint128"},{"name":"currentLiquidityRate","type":"uint128"},{"name":"variableBorrowIndex","type":"uint128"},{"name":"currentVariableBorrowRate","type":"uint128"},{"name":"currentStableBorrowRate","type":"uint128"},{"name":"lastUpdateTimestamp","type":"uint40"},{"name":"id","type":"uint16"},{"name":"aTokenAddress","type":"address"},{"name":"stableDebtTokenAddress","type":"address"},{"name":"variableDebtTokenAddress","type":"address"},{"name":"interestRateStrategyAddress","type":"address"},{"name":"accruedToTreasury","type":"uint128"},{"name":"unbacked","type":"uint128"},{"name":"isolationModeTotalDebt","type":"uint128"}],"name":"","type":"tuple"}],"stateMutability":"view","type":"function"}]
                )
                
                # Get aToken balance for available liquidity
                reserve_data = aave_pool.functions.getReserveData(token_address).call()
                atoken_address = reserve_data[8]
                
                token_contract = self.w3.eth.contract(
                    address=token_address,
                    abi=[{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]
                )
                
                available = token_contract.functions.balanceOf(atoken_address).call()
                
                if 'aave_v3' not in limits:
                    limits['aave_v3'] = {}
                limits['aave_v3'][token_symbol] = available
                
            except Exception as e:
                print(f"Error getting {token_symbol} limit: {e}")
                limits['aave_v3'][token_symbol] = 0
        
        # Balancer - Query vault balance
        for token_symbol, token_address in self.token_addresses.items():
            try:
                token_contract = self.w3.eth.contract(
                    address=token_address,
                    abi=[{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]
                )
                
                vault_balance = token_contract.functions.balanceOf(self.protocols['balancer']['address']).call()
                
                if 'balancer' not in limits:
                    limits['balancer'] = {}
                limits['balancer'][token_symbol] = vault_balance
                
            except:
                limits['balancer'][token_symbol] = 0
        
        return limits
    
    def __init__(self, w3):
        self.w3 = w3
        # Update protocol list with real values
        self.update_protocol_limits()
    
    async def update_protocol_limits(self):
        """Update limits with real-time data"""
        real_limits = await self.get_real_protocol_limits()
        for protocol_name, token_limits in real_limits.items():
            if protocol_name in self.protocols:
                self.protocols[protocol_name]['limits'] = token_limits

    def __init_old__(self, w3):
        self.w3 = w3
        
        self.protocols = {
            'aave_v3': {
                'address': config.config['contracts'].get('contract_name', '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'),
                'limits': {}  # Will be populated dynamically,
                'fee': 0.0009,
                'function': 'flashLoanSimple'
            },
            'balancer': {
                'address': config.config['contracts'].get('contract_name', '0xBA12222222228d8Ba445958a75a0704d566BF2C8'),
                'limits': {}  # Will be populated dynamically,
                'fee': 0,
                'function': 'flashLoan'
            },
            'dydx': {
                'address': config.config['contracts'].get('contract_name', '0x1E0447b19BB6EcFdAe1e4AE1694b0C3659614e4e'),
                'limits': {}  # Will be populated dynamically,
                'fee': 0.0002,
                'function': 'operate'
            },
            'uniswap_v3': {
                'address': config.config['contracts'].get('contract_name', '0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640'),
                'limits': {}  # Will be populated dynamically,
                'fee': 0.0005,
                'function': 'flash'
            },
            'compound': {
                'address': config.config['contracts'].get('contract_name', '0xc3d688B66703497DAA19211EEdff47f25384cdc3'),
                'limits': {}  # Will be populated dynamically,
                'fee': 0.0009,
                'function': 'flashLoan'
            },
            'maker': {
                'address': config.config['contracts'].get('contract_name', '0x60744434d6339a6B27d73d9Eda62b6F66a0a04FA'),
                'limits': {}  # Will be populated dynamically,
                'fee': 0,
                'function': 'flashLoan'
            }
        }
        
        self.token_addresses = {
            'USDC': config.config['contracts'].get('contract_name', '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            'USDT': config.config['contracts'].get('contract_name', '0xdAC17F958D2ee523a2206206994597C13D831ec7'),
            'DAI': config.config['contracts'].get('contract_name', '0x6B175474E89094C44Da98b954EedeAC495271d0F'),
            'WETH': config.config['contracts'].get('contract_name', '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
        }
    
    async def get_optimal_loans(self, required_amount: int, token: str = 'USDC') -> List[Dict]:
        sorted_protocols = sorted(
            [(name, proto) for name, proto in self.protocols.items() if token in proto['limits']],
            key=lambda x: x[1]['fee']
        )
        
        loans = []
        remaining = required_amount
        total_fees = 0
        
        for protocol_name, protocol in sorted_protocols:
            if remaining <= 0:
                break
            
            available = protocol['limits'].get(token, 0)
            borrow_amount = min(remaining, int(available * 0.95))
            
            if borrow_amount > 10000000 * 10**6:
                fee = borrow_amount * protocol['fee']
                
                loans.append({
                    'protocol': protocol_name,
                    'address': protocol['address'],
                    'token': self.token_addresses[token],
                    'amount': borrow_amount,
                    'fee': fee,
                    'function': protocol['function']
                })
                
                remaining -= borrow_amount
                total_fees += fee
        
        return loans
    
    async def get_maximum_loans(self) -> List[Dict]:
        all_loans = []
        
        for token in ['USDC', 'USDT', 'DAI', 'WETH']:
            max_available = sum(
                proto['limits'].get(token, 0) 
                for proto in self.protocols.values()
            )
            
            if max_available > 0:
                loans = await self.get_optimal_loans(max_available, token)
                all_loans.extend(loans)
        
        return all_loans
    
    def encode_flash_loan_call(self, loan: Dict) -> str:
        protocol = loan['protocol']
        
        if protocol == 'aave_v3':
            return self.encode_aave_flash_loan(loan)
        elif protocol == 'balancer':
            return self.encode_balancer_flash_loan(loan)
        elif protocol == 'dydx':
            return self.encode_dydx_flash_loan(loan)
        elif protocol == 'uniswap_v3':
            return self.encode_uniswap_flash_loan(loan)
        elif protocol == 'compound':
            return self.encode_compound_flash_loan(loan)
        elif protocol == 'maker':
            return self.encode_maker_flash_loan(loan)
    
    def encode_aave_flash_loan(self, loan: Dict) -> str:
        function_sig = Web3.keccak(text='flashLoanSimple(address,address,uint256,bytes,uint16)')[:4]
        receiver = Web3.toBytes(hexstr=loan['receiver'])
        asset = Web3.toBytes(hexstr=loan['token'])
        amount = Web3.toBytes(loan['amount']).rjust(32, b'\x00')
        params = Web3.toBytes(hexstr='0x')
        referral = Web3.toBytes(0).rjust(32, b'\x00')
        
        return Web3.toHex(function_sig + receiver + asset + amount + params + referral)
    
    def encode_balancer_flash_loan(self, loan: Dict) -> str:
        function_sig = Web3.keccak(text='flashLoan(address,address[],uint256[],bytes)')[:4]
        recipient = Web3.toBytes(hexstr=loan['receiver'])
        
        return Web3.toHex(function_sig + recipient)
    
    def encode_dydx_flash_loan(self, loan: Dict) -> str:
        function_sig = Web3.keccak(text='operate((address,uint256)[],(uint8,uint256,address,uint256,uint128,uint128,address,bytes)[])')[:4]
        return Web3.toHex(function_sig)
    
    def encode_uniswap_flash_loan(self, loan: Dict) -> str:
        function_sig = Web3.keccak(text='flash(address,uint256,uint256,bytes)')[:4]
        recipient = Web3.toBytes(hexstr=loan['receiver'])
        amount0 = Web3.toBytes(loan['amount'] if loan['token'] == self.token_addresses['USDC'] else 0).rjust(32, b'\x00')
        amount1 = Web3.toBytes(loan['amount'] if loan['token'] == self.token_addresses['WETH'] else 0).rjust(32, b'\x00')
        
        return Web3.toHex(function_sig + recipient + amount0 + amount1)
    
    def encode_compound_flash_loan(self, loan: Dict) -> str:
        function_sig = Web3.keccak(text='flashLoan(address,uint256)')[:4]
        asset = Web3.toBytes(hexstr=loan['token'])
        amount = Web3.toBytes(loan['amount']).rjust(32, b'\x00')
        
        return Web3.toHex(function_sig + asset + amount)
    
    def encode_maker_flash_loan(self, loan: Dict) -> str:
        function_sig = Web3.keccak(text='flashLoan(address,uint256)')[:4]
        receiver = Web3.toBytes(hexstr=loan['receiver'])
        amount = Web3.toBytes(loan['amount']).rjust(32, b'\x00')
        
        return Web3.toHex(function_sig + receiver + amount)
    
    async def check_available_liquidity(self) -> Dict:
        current_liquidity = {}
        
        for protocol_name, protocol in self.protocols.items():
            for token, max_amount in protocol['limits'].items():
                actual_available = await self.get_actual_available(protocol['address'], token)
                
                if protocol_name not in current_liquidity:
                    current_liquidity[protocol_name] = {}
                
                current_liquidity[protocol_name][token] = min(actual_available, max_amount)
        
        return current_liquidity
    
    async def get_actual_available(self, protocol_address: str, token: str) -> int:
        token_address = self.token_addresses[token]
        
        token_contract = self.w3.eth.contract(
            address=Web3.toChecksumAddress(token_address),
            abi=[{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]
        )
        
        try:
            balance = token_contract.functions.balanceOf(protocol_address).call()
            return balance
        except:
            return 0
    
    def calculate_total_available(self) -> Dict:
        totals = {}
        
        for token in self.token_addresses.keys():
            total = sum(
                proto['limits'].get(token, 0)
                for proto in self.protocols.values()
            )
            totals[token] = total
        
        return totals
    
    def get_cheapest_source(self, amount: int, token: str = 'USDC') -> Dict:
        valid_protocols = [
            (name, proto) for name, proto in self.protocols.items()
            if token in proto['limits'] and proto['limits'][token] >= amount
        ]
        
        if not valid_protocols:
            return None
        
        cheapest = min(valid_protocols, key=lambda x: x[1]['fee'])
        
        return {
            'protocol': cheapest[0],
            'address': cheapest[1]['address'],
            'fee': cheapest[1]['fee'],
            'available': cheapest[1]['limits'][token]
        }