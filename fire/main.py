# main_integrated.py
from datetime import datetime, timezone
import asyncio
import os
import sys
from web3 import Web3

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from core.rust_bridge import RustBridge

class IntegratedMEVBot:
    def __init__(self):
        self.config = Config()
        self.w3 = Web3(Web3.HTTPProvider(f"https://eth-sepolia.g.alchemy.com/v2/{self.config.ALCHEMY_API_KEY}"))
        self.rust_bridge = RustBridge()
        self.is_running = False
        self.start_time = datetime.now(timezone.utc)
        
    async def initialize(self):
        print("Initializing Integrated MEV Bot...")
        print("Compiling Rust components...")
        
        try:
            await self.rust_bridge.compile_rust()
            print("Rust components compiled successfully")
        except Exception as e:
            print(f"Warning: Rust compilation failed, continuing with Python: {e}")
        
        balance = self.w3.eth.get_balance(self.config.WALLET_ADDRESS)
        print(f"Wallet: {self.config.WALLET_ADDRESS}")
        print(f"Balance: {Web3.from_wei(balance, 'ether'):.4f} ETH")
        print(f"Network: {'Mainnet' if self.w3.eth.chain_id == 1 else f'Chain {self.w3.eth.chain_id}'}")
        
    async def start(self):
        await self.initialize()
        
        print("\n" + "="*50)
        print("   Integrated MEV Bot Started")
        print("   Running Rust + Python Hybrid")
        print("="*50 + "\n")
        
        self.is_running = True
        
        try:
            await self.rust_bridge.start_rust_scanner()
            print("Rust scanner started - monitoring all chains")
        except:
            print("Rust scanner failed to start, using Python fallback")
        
        while self.is_running:
            try:
                current_block = self.w3.eth.block_number
                gas_price = self.w3.eth.gas_price
                
                print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Block: {current_block} | Gas: {Web3.from_wei(gas_price, 'gwei'):.2f} gwei | Rust: {'Active' if self.rust_bridge.rust_process else 'Inactive'}")
                
                await asyncio.sleep(10)
                
            except KeyboardInterrupt:
                print("\nShutting down...")
                self.is_running = False
                break
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(10)
        
        self.rust_bridge.stop()

if __name__ == "__main__":
    bot = IntegratedMEVBot()
    asyncio.run(bot.start())