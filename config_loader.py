#!/usr/bin/env python3
"""
Configuration loader for MEV bot
Loads settings from environment variables and config files
"""

import os
import json
from typing import Dict, Any
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

class ConfigLoader:
    def __init__(self):
        self.config = self.load_config()
        self.validate_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from multiple sources"""
        config = {}
        
        # Load from JSON config if exists
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                config = json.load(f)
        
        # Override with environment variables
        config['rpc_url'] = os.getenv('RPC_URL', config.get('rpc_url', 'https://eth.llamarpc.com'))
        config['private_key'] = os.getenv('PRIVATE_KEY', '')
        config['flashbots_auth_key'] = os.getenv('FLASHBOTS_AUTH_KEY', '')
        
        # API keys from environment
        config['api_keys'] = {
            'alchemy': os.getenv('ALCHEMY_KEY', ''),
            'infura': os.getenv('INFURA_KEY', ''),
            'bloxroute': os.getenv('BLOXROUTE_KEY', ''),
            'blocknative': os.getenv('BLOCKNATIVE_KEY', ''),
            'etherscan': os.getenv('ETHERSCAN_KEY', '')
        }
        
        # Dynamic contract addresses - fetch from registry or config
        config['contracts'] = self.load_contract_addresses()
        
        # Dynamic oracle addresses
        config['oracles'] = self.load_oracle_addresses()
        
        return config
    
    def load_contract_addresses(self) -> Dict[str, str]:
        """Load contract addresses dynamically"""
        # These could be fetched from on-chain registry
        contracts = {}
        
        # Try to load from contracts.json
        if os.path.exists('contracts.json'):
            with open('contracts.json', 'r') as f:
                contracts = json.load(f)
        else:
            # Use known mainnet addresses as defaults
            contracts = {
                'aave_v3_pool': Web3.to_checksum_address('0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'),
                'compound_v3': Web3.to_checksum_address('0xc3d688B66703497DAA19211EEdff47f25384cdc3'),
                'balancer_vault': Web3.to_checksum_address('0xBA12222222228d8Ba445958a75a0704d566BF2C8'),
                'uniswap_v2_router': Web3.to_checksum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
                'uniswap_v3_router': Web3.to_checksum_address('0xE592427A0AEce92De3Edee1F18E0157C05861564')
            }
        
        return contracts
    
    def load_oracle_addresses(self) -> Dict[str, str]:
        """Load oracle addresses dynamically"""
        oracles = {}
        
        # Try to load from oracles.json
        if os.path.exists('oracles.json'):
            with open('oracles.json', 'r') as f:
                oracles = json.load(f)
        else:
            # Chainlink oracle addresses
            oracles = {
                'ETH/USD': Web3.to_checksum_address('0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419'),
                'BTC/USD': Web3.to_checksum_address('0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c'),
                'USDC/USD': Web3.to_checksum_address('0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6')
            }
        
        return oracles
    
    def validate_config(self):
        """Validate configuration"""
        if not self.config.get('private_key'):
            print("⚠️  Warning: No private key configured")
        
        if not any(self.config.get('api_keys', {}).values()):
            print("⚠️  Warning: No API keys configured")
    
    def get_web3_instance(self, network: str = 'mainnet') -> Web3:
        """Get Web3 instance with fallback providers"""
        providers = []
        
        # Add configured providers
        if self.config['api_keys']['alchemy']:
            providers.append(f"https://eth-mainnet.g.alchemy.com/v2/{self.config['api_keys']['alchemy']}")
        
        if self.config['api_keys']['infura']:
            providers.append(f"https://mainnet.infura.io/v3/{self.config['api_keys']['infura']}")
        
        # Add public providers as fallback
        providers.extend([
            'https://eth.llamarpc.com',
            'https://rpc.ankr.com/eth',
            'https://cloudflare-eth.com',
            'https://rpc.flashbots.net'
        ])
        
        # Try each provider
        for provider_url in providers:
            try:
                w3 = Web3(Web3.HTTPProvider(provider_url))
                if w3.is_connected():
                    return w3
            except:
                continue
        
        raise Exception("Could not connect to any Web3 provider")

# Singleton instance
config = ConfigLoader()
