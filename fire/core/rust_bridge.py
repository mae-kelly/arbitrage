# core/rust_bridge.py
import subprocess
import json
import asyncio
import os
from typing import Dict, List, Any

class RustBridge:
    def __init__(self):
        self.rust_process = None
        self.config = self._load_config()
        
    def _load_config(self):
        from dotenv import load_dotenv
        load_dotenv('.env')
        
        return {
            'private_key': os.getenv('PRIVATE_KEY'),
            'wallet_address': os.getenv('WALLET_ADDRESS'),
            'alchemy_key': os.getenv('ALCHEMY_API_KEY'),
            'flashloan_contract': os.getenv('FLASHLOAN_CONTRACT_ADDRESS', '0x0000000000000000000000000000000000000000')
        }
    
    async def compile_rust(self):
        os.chdir('rust_ws')
        result = subprocess.run(['cargo', 'build', '--release'], capture_output=True, text=True)
        os.chdir('../..')
        if result.returncode != 0:
            raise Exception(f"Rust compilation failed: {result.stderr}")
        return True
    
    async def start_rust_scanner(self):
        self.rust_process = subprocess.Popen(
            ['core/rust_ws/target/release/mev_scanner'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        asyncio.create_task(self._read_rust_output())
        
    async def _read_rust_output(self):
        while True:
            if self.rust_process:
                line = self.rust_process.stdout.readline()
                if line:
                    await self._process_rust_message(line.strip())
            await asyncio.sleep(0.001)
    
    async def _process_rust_message(self, message: str):
        if "DEX transaction detected" in message:
            parts = message.split(' - ')
            if len(parts) == 2:
                chain_and_hash = parts[1]
                await self.execute_arbitrage_from_rust(chain_and_hash)
        elif "Price:" in message:
            self._update_price_cache(message)
    
    def _update_price_cache(self, price_message: str):
        pass
    
    async def execute_arbitrage_from_rust(self, opportunity_data: str):
        try:
            subprocess.run([
                'core/rust_ws/target/release/mev_scanner',
                '--execute',
                opportunity_data,
                '--private-key', self.config['private_key'],
                '--wallet', self.config['wallet_address']
            ])
        except Exception as e:
            print(f"Execution failed: {e}")
    
    def stop(self):
        if self.rust_process:
            self.rust_process.terminate()
            self.rust_process.wait()