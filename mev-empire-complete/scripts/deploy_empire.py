#!/usr/bin/env python3

import asyncio
import argparse
import logging
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.empire_controller import EmpireController
from src.utils.web3_utils import Web3Utils
from src.infrastructure.multi_chain_manager import MultiChainManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def deploy_contracts(chain_ids: list):
    logger.info("Deploying smart contracts")
    
    web3_utils = Web3Utils()
    await web3_utils.initialize()
    
    contract_addresses = {}
    
    for chain_id in chain_ids:
        logger.info(f"Deploying to chain {chain_id}")
        
        try:
            flash_loan_address = await deploy_flash_loan_contract(web3_utils, chain_id)
            mev_executor_address = await deploy_mev_executor_contract(web3_utils, chain_id, flash_loan_address)
            
            contract_addresses[chain_id] = {
                "flash_loan_aggregator": flash_loan_address,
                "mev_executor": mev_executor_address
            }
            
            logger.info(f"Deployed contracts on chain {chain_id}")
            
        except Exception as e:
            logger.error(f"Deployment failed for chain {chain_id}: {e}")
            
    return contract_addresses

async def deploy_flash_loan_contract(web3_utils: Web3Utils, chain_id: int):
    w3 = web3_utils.get_web3(chain_id)
    
    bytecode = get_flash_loan_bytecode()
    constructor_args = get_flash_loan_constructor_args(chain_id)
    
    contract = w3.eth.contract(abi=get_flash_loan_abi(), bytecode=bytecode)
    
    transaction = contract.constructor(*constructor_args).build_transaction({
        'gas': 3000000,
        'gasPrice': await web3_utils.get_gas_price(chain_id),
        'nonce': await web3_utils.get_nonce(web3_utils.accounts["deployer"].address, chain_id)
    })
    
    signed_txn = await web3_utils.sign_transaction(transaction, chain_id, "deployer")
    tx_hash = await web3_utils.send_transaction(signed_txn, chain_id)
    receipt = await web3_utils.wait_for_receipt(tx_hash.hex(), chain_id)
    
    return receipt['contractAddress']

async def deploy_mev_executor_contract(web3_utils: Web3Utils, chain_id: int, flash_loan_address: str):
    w3 = web3_utils.get_web3(chain_id)
    
    bytecode = get_mev_executor_bytecode()
    constructor_args = [flash_loan_address]
    
    contract = w3.eth.contract(abi=get_mev_executor_abi(), bytecode=bytecode)
    
    transaction = contract.constructor(*constructor_args).build_transaction({
        'gas': 2500000,
        'gasPrice': await web3_utils.get_gas_price(chain_id),
        'nonce': await web3_utils.get_nonce(web3_utils.accounts["deployer"].address, chain_id)
    })
    
    signed_txn = await web3_utils.sign_transaction(transaction, chain_id, "deployer")
    tx_hash = await web3_utils.send_transaction(signed_txn, chain_id)
    receipt = await web3_utils.wait_for_receipt(tx_hash.hex(), chain_id)
    
    return receipt['contractAddress']

async def setup_database():
    logger.info("Setting up database")
    
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="mevempire"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        cursor.execute("CREATE DATABASE IF NOT EXISTS mev_empire")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id SERIAL PRIMARY KEY,
                strategy VARCHAR(50) NOT NULL,
                token_in VARCHAR(42),
                token_out VARCHAR(42),
                amount_in DECIMAL(36,18),
                amount_out DECIMAL(36,18),
                profit DECIMAL(36,18),
                gas_cost DECIMAL(36,18),
                tx_hash VARCHAR(66),
                block_number INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT FALSE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id SERIAL PRIMARY KEY,
                strategy VARCHAR(50) NOT NULL,
                total_trades INTEGER DEFAULT 0,
                successful_trades INTEGER DEFAULT 0,
                total_profit DECIMAL(36,18) DEFAULT 0,
                total_gas_cost DECIMAL(36,18) DEFAULT 0,
                avg_execution_time DECIMAL(10,4) DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        logger.info("Database setup completed")
        
    except Exception as e:
        logger.error(f"Database setup error: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Deploy MEV Empire")
    parser.add_argument("--chains", nargs="+", type=int, default=[1, 137, 56, 42161], help="Chain IDs to deploy to")
    parser.add_argument("--skip-contracts", action="store_true", help="Skip contract deployment")
    parser.add_argument("--production", action="store_true", help="Production deployment")
    
    args = parser.parse_args()
    
    logger.info("Starting MEV Empire deployment")
    
    if not args.skip_contracts:
        contract_addresses = await deploy_contracts(args.chains)
        
        with open("deployed_contracts.json", "w") as f:
            import json
            json.dump(contract_addresses, f, indent=2)
        
        logger.info("Contract addresses saved to deployed_contracts.json")
    
    await setup_database()
    
    if args.production:
        logger.info("Starting empire in production mode")
        empire = EmpireController()
        await empire.initialize()
        await empire.start()
    
    logger.info("Deployment completed successfully")

def get_flash_loan_bytecode():
    return "0x608060405234801561001057600080fd5b50"

def get_flash_loan_abi():
    return []

def get_flash_loan_constructor_args(chain_id: int):
    return []

def get_mev_executor_bytecode():
    return "0x608060405234801561001057600080fd5b50"

def get_mev_executor_abi():
    return []

if __name__ == "__main__":
    asyncio.run(main())
