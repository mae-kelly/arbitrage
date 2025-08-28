import os
from dotenv import load_dotenv
from web3 import Web3

# Load environment variables
load_dotenv('.env')

class Config:
    # Wallet configuration
    WALLET_ADDRESS = Web3.to_checksum_address(os.getenv('WALLET_ADDRESS'))
    PRIVATE_KEY = os.getenv('PRIVATE_KEY')
    
    # RPC URLs
    ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY')
    INFURA_API_KEY = os.getenv('INFURA_API_KEY', '')  # Optional
    RPC_URL = f"https://eth-sepolia.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
    
    # Exchange API keys
    OKX_API_KEY = os.getenv('OKX_API_KEY', '')
    OKX_SECRET_KEY = os.getenv('OKX_SECRET_KEY', '')
    OKX_PASSPHRASE = os.getenv('OKX_PASSPHRASE', '')
    
    # DEX Addresses (Sepolia testnet)
    DEX_ADDRESSES = {
        'uniswap_v3_router': '0x3bFA4769FB09eefC5a80d6E87c3B9C650f7Ae48E',
        'uniswap_v2_router': '0xC532a74256D3Db42D0Bf7a0400fEFDbad7694008',
        'sushiswap_router': '0x0000000000000000000000000000000000000000',
        'curve_router': '0x0000000000000000000000000000000000000000'
    }
    
    # Token addresses (Sepolia testnet) - TOKENS alias for TOKEN_ADDRESSES
    TOKEN_ADDRESSES = {
        'WETH': '0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14',
        'USDC': '0x94a9D9AC8a22534E3FaCa9F4e7F2E2cf85d5E4C8',
        'DAI': '0x68194a729C2450ad26072b3D33ADaCbcef39D574',
        'USDT': '0xaA8E23Fb1079EA71e0a56F48a2aA51851D8433D0'
    }
    TOKENS = TOKEN_ADDRESSES  # Alias for compatibility
    
    # Contract addresses
    FLASHLOAN_CONTRACT_ADDRESS = os.getenv('FLASHLOAN_CONTRACT_ADDRESS', '0x0000000000000000000000000000000000000000')
    if FLASHLOAN_CONTRACT_ADDRESS and FLASHLOAN_CONTRACT_ADDRESS != '0x0000000000000000000000000000000000000000':
        FLASHLOAN_CONTRACT_ADDRESS = Web3.to_checksum_address(FLASHLOAN_CONTRACT_ADDRESS)
    
    # Discord webhook
    DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')
    
    # Trading parameters
    MIN_PROFIT_THRESHOLD = float(os.getenv('MIN_PROFIT_THRESHOLD', '0.01'))
    MAX_SLIPPAGE = float(os.getenv('MAX_SLIPPAGE', '0.005'))
    GAS_PRICE_MULTIPLIER = float(os.getenv('GAS_PRICE_MULTIPLIER', '1.2'))
    
    # Network configuration
    CHAIN_ID = 11155111  # Sepolia
    NETWORK = 'sepolia'
