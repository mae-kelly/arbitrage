import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from web3 import Web3
from eth_abi import encode_abi, decode_abi

logger = logging.getLogger(__name__)

class UniswapV3Integration:
    def __init__(self, web3: Web3):
        self.web3 = web3
        self.factory_address = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
        self.router_address = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
        self.quoter_address = "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6"
        
        self.factory_contract = None
        self.router_contract = None
        self.quoter_contract = None
        self.pool_cache = {}
        
    async def initialize(self):
        logger.info("Initializing Uniswap V3 integration")
        
        try:
            self.factory_contract = self.web3.eth.contract(
                address=self.factory_address,
                abi=self._get_factory_abi()
            )
            
            self.router_contract = self.web3.eth.contract(
                address=self.router_address,
                abi=self._get_router_abi()
            )
            
            self.quoter_contract = self.web3.eth.contract(
                address=self.quoter_address,
                abi=self._get_quoter_abi()
            )
            
            await self._load_popular_pools()
            
            logger.info("Uniswap V3 integration initialized")
            
        except Exception as e:
            logger.error(f"Uniswap V3 initialization error: {e}")
            raise
    
    async def get_pool_address(self, token0: str, token1: str, fee: int) -> str:
        try:
            pool_key = f"{token0}_{token1}_{fee}"
            
            if pool_key in self.pool_cache:
                return self.pool_cache[pool_key]
            
            pool_address = self.factory_contract.functions.getPool(
                token0, token1, fee
            ).call()
            
            if pool_address != "0x0000000000000000000000000000000000000000":
                self.pool_cache[pool_key] = pool_address
                return pool_address
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting pool address: {e}")
            return None
    
    async def get_quote(self, token_in: str, token_out: str, amount_in: int, fee: int = 3000) -> Optional[int]:
        try:
            quote = self.quoter_contract.functions.quoteExactInputSingle(
                token_in,
                token_out,
                fee,
                amount_in,
                0
            ).call()
            
            return quote
            
        except Exception as e:
            logger.error(f"Error getting quote: {e}")
            return None
    
    async def execute_swap(self, token_in: str, token_out: str, amount_in: int, 
                          min_amount_out: int, fee: int = 3000, 
                          recipient: str = None) -> Dict[str, Any]:
        try:
            if not recipient:
                recipient = self.web3.eth.default_account
            
            deadline = self.web3.eth.get_block('latest')['timestamp'] + 300
            
            swap_params = {
                'tokenIn': token_in,
                'tokenOut': token_out,
                'fee': fee,
                'recipient': recipient,
                'deadline': deadline,
                'amountIn': amount_in,
                'amountOutMinimum': min_amount_out,
                'sqrtPriceLimitX96': 0
            }
            
            transaction = self.router_contract.functions.exactInputSingle(
                swap_params
            ).build_transaction({
                'gas': 300000,
                'gasPrice': self.web3.eth.gas_price
            })
            
            signed_txn = self.web3.eth.account.sign_transaction(
                transaction, 
                private_key=self.web3.eth.default_account
            )
            
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                "success": receipt['status'] == 1,
                "tx_hash": tx_hash.hex(),
                "gas_used": receipt['gasUsed'],
                "block_number": receipt['blockNumber']
            }
            
        except Exception as e:
            logger.error(f"Swap execution error: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_flash_swap(self, token0: str, token1: str, amount0: int, 
                                amount1: int, callback_data: bytes) -> Dict[str, Any]:
        try:
            pool_address = await self.get_pool_address(token0, token1, 3000)
            if not pool_address:
                return {"success": False, "error": "Pool not found"}
            
            pool_contract = self.web3.eth.contract(
                address=pool_address,
                abi=self._get_pool_abi()
            )
            
            transaction = pool_contract.functions.flash(
                self.web3.eth.default_account,
                amount0,
                amount1,
                callback_data
            ).build_transaction({
                'gas': 500000,
                'gasPrice': self.web3.eth.gas_price
            })
            
            signed_txn = self.web3.eth.account.sign_transaction(
                transaction,
                private_key=self.web3.eth.default_account
            )
            
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                "success": receipt['status'] == 1,
                "tx_hash": tx_hash.hex(),
                "gas_used": receipt['gasUsed']
            }
            
        except Exception as e:
            logger.error(f"Flash swap error: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_pool_liquidity(self, token0: str, token1: str, fee: int) -> Dict[str, Any]:
        try:
            pool_address = await self.get_pool_address(token0, token1, fee)
            if not pool_address:
                return None
            
            pool_contract = self.web3.eth.contract(
                address=pool_address,
                abi=self._get_pool_abi()
            )
            
            liquidity = pool_contract.functions.liquidity().call()
            slot0 = pool_contract.functions.slot0().call()
            
            return {
                "liquidity": liquidity,
                "sqrt_price_x96": slot0[0],
                "tick": slot0[1],
                "fee_growth_global_0_x128": pool_contract.functions.feeGrowthGlobal0X128().call(),
                "fee_growth_global_1_x128": pool_contract.functions.feeGrowthGlobal1X128().call()
            }
            
        except Exception as e:
            logger.error(f"Error getting pool liquidity: {e}")
            return None
    
    async def _load_popular_pools(self):
        popular_pairs = [
            ("0xA0b86a33E6441Fb63F1Fa8087fFF1E71cC51D8E2", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 3000),
            ("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "0xdAC17F958D2ee523a2206206994597C13D831ec7", 3000),
            ("0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 3000),
        ]
        
        for token0, token1, fee in popular_pairs:
            pool_address = await self.get_pool_address(token0, token1, fee)
            if pool_address:
                pool_key = f"{token0}_{token1}_{fee}"
                self.pool_cache[pool_key] = pool_address
    
    def _get_factory_abi(self) -> List[Dict]:
        return [
            {
                "inputs": [
                    {"internalType": "address", "name": "tokenA", "type": "address"},
                    {"internalType": "address", "name": "tokenB", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"}
                ],
                "name": "getPool",
                "outputs": [{"internalType": "address", "name": "pool", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    def _get_router_abi(self) -> List[Dict]:
        return [
            {
                "inputs": [
                    {
                        "components": [
                            {"internalType": "address", "name": "tokenIn", "type": "address"},
                            {"internalType": "address", "name": "tokenOut", "type": "address"},
                            {"internalType": "uint24", "name": "fee", "type": "uint24"},
                            {"internalType": "address", "name": "recipient", "type": "address"},
                            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                            {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                        ],
                        "internalType": "struct ISwapRouter.ExactInputSingleParams",
                        "name": "params",
                        "type": "tuple"
                    }
                ],
                "name": "exactInputSingle",
                "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
                "stateMutability": "payable",
                "type": "function"
            }
        ]
    
    def _get_quoter_abi(self) -> List[Dict]:
        return [
            {
                "inputs": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                ],
                "name": "quoteExactInputSingle",
                "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
    
    def _get_pool_abi(self) -> List[Dict]:
        return [
            {
                "inputs": [
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "amount0", "type": "uint256"},
                    {"internalType": "uint256", "name": "amount1", "type": "uint256"},
                    {"internalType": "bytes", "name": "data", "type": "bytes"}
                ],
                "name": "flash",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "liquidity",
                "outputs": [{"internalType": "uint128", "name": "", "type": "uint128"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "slot0",
                "outputs": [
                    {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
                    {"internalType": "int24", "name": "tick", "type": "int24"},
                    {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
                    {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
                    {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
                    {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
                    {"internalType": "bool", "name": "unlocked", "type": "bool"}
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]
