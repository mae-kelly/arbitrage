import asyncio
import json
from web3 import Web3
from eth_account import Account
from decimal import Decimal
import os
import time

class RealMEVBot:
    def __init__(self):
        self.setup_connections()
        self.load_accounts()
        self.token_addresses = {
            'WETH': Web3.to_checksum_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
            'USDC': Web3.to_checksum_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            'USDT': Web3.to_checksum_address('0xdAC17F958D2ee523a2206206994597C13D831ec7'),
            'DAI': Web3.to_checksum_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),
            'WBTC': Web3.to_checksum_address('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599')
        }
        
    def setup_connections(self):
        try:
            if os.path.exists('.env'):
                with open('.env', 'r') as f:
                    for line in f:
                        if 'ALCHEMY_KEY=' in line:
                            key = line.split('=')[1].strip().strip('"')
                            if key and key != 'demo':
                                self.w3 = Web3(Web3.HTTPProvider(f'https://eth-mainnet.g.alchemy.com/v2/{key}'))
                                if self.w3.is_connected():
                                    print(f"Connected to Ethereum via Alchemy")
                                    return
            
            self.w3 = Web3(Web3.HTTPProvider('https://rpc.ankr.com/eth'))
            if self.w3.is_connected():
                print(f"Connected to Ethereum via Ankr (free)")
        except:
            self.w3 = Web3(Web3.HTTPProvider('https://cloudflare-eth.com'))
            print(f"Connected to Ethereum via Cloudflare")
    
    def load_accounts(self):
        try:
            with open('.keys.json', 'r') as f:
                keys = json.load(f)
                self.account = Account.from_key(keys['main']['private_key'])
                print(f"Loaded account: {self.account.address}")
        except:
            self.account = Account.create()
            print(f"Created new account: {self.account.address}")
    
    def get_uniswap_v2_pair(self, token0, token1):
        factory = self.w3.eth.contract(
            address='0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f',
            abi=[{"constant":True,"inputs":[{"name":"","type":"address"},{"name":"","type":"address"}],"name":"getPair","outputs":[{"name":"","type":"address"}],"type":"function"}]
        )
        return factory.functions.getPair(token0, token1).call()
    
    def get_reserves(self, pair_address):
        pair = self.w3.eth.contract(
            address=pair_address,
            abi=[{"constant":True,"inputs":[],"name":"getReserves","outputs":[{"name":"_reserve0","type":"uint112"},{"name":"_reserve1","type":"uint112"},{"name":"_blockTimestampLast","type":"uint32"}],"type":"function"}]
        )
        return pair.functions.getReserves().call()
    
    def calculate_price(self, reserve0, reserve1, decimals0=18, decimals1=18):
        if reserve0 == 0:
            return 0
        price = (reserve1 / 10**decimals1) / (reserve0 / 10**decimals0)
        return price
    
    def find_arbitrage(self):
        opportunities = []
        
        weth = self.token_addresses['WETH']
        usdc = self.token_addresses['USDC']
        
        uniswap_pair = self.get_uniswap_v2_pair(weth, usdc)
        if uniswap_pair != '0x0000000000000000000000000000000000000000':
            uni_reserves = self.get_reserves(uniswap_pair)
            uni_price = self.calculate_price(uni_reserves[0], uni_reserves[1], 18, 6)
            
            sushi_factory = self.w3.eth.contract(
                address='0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac',
                abi=[{"constant":True,"inputs":[{"name":"","type":"address"},{"name":"","type":"address"}],"name":"getPair","outputs":[{"name":"","type":"address"}],"type":"function"}]
            )
            sushi_pair = sushi_factory.functions.getPair(weth, usdc).call()
            
            if sushi_pair != '0x0000000000000000000000000000000000000000':
                sushi_reserves = self.get_reserves(sushi_pair)
                sushi_price = self.calculate_price(sushi_reserves[0], sushi_reserves[1], 18, 6)
                
                price_diff = abs(uni_price - sushi_price) / min(uni_price, sushi_price) if min(uni_price, sushi_price) > 0 else 0
                
                if price_diff > 0.002:
                    opportunities.append({
                        'type': 'arbitrage',
                        'dex1': 'Uniswap',
                        'dex2': 'Sushiswap',
                        'token_pair': 'WETH/USDC',
                        'price1': uni_price,
                        'price2': sushi_price,
                        'price_diff_pct': price_diff * 100,
                        'estimated_profit': price_diff * 100000
                    })
        
        return opportunities
    
    def check_liquidations(self):
        aave_pool = self.w3.eth.contract(
            address='0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2',
            abi=[{"inputs":[{"name":"user","type":"address"}],"name":"getUserAccountData","outputs":[{"name":"totalCollateralETH","type":"uint256"},{"name":"totalDebtETH","type":"uint256"},{"name":"availableBorrowsETH","type":"uint256"},{"name":"currentLiquidationThreshold","type":"uint256"},{"name":"ltv","type":"uint256"},{"name":"healthFactor","type":"uint256"}],"stateMutability":"view","type":"function"}]
        )
        
        recent_borrowers = []
        current_block = self.w3.eth.block_number
        
        filter_params = {
            'fromBlock': current_block - 100,
            'toBlock': current_block,
            'address': '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2',
            'topics': ['0xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0']
        }
        
        liquidatable = []
        
        for borrower in recent_borrowers[:10]:
            try:
                data = aave_pool.functions.getUserAccountData(borrower).call()
                health_factor = data[5] / 10**18
                
                if health_factor < 1.05 and health_factor > 0:
                    liquidatable.append({
                        'user': borrower,
                        'health_factor': health_factor,
                        'total_debt_eth': data[1] / 10**18,
                        'total_collateral_eth': data[0] / 10**18,
                        'max_liquidation': (data[1] / 10**18) * 0.5
                    })
            except:
                continue
        
        return liquidatable
    
    def build_sandwich_bundle(self, target_tx):
        target_value = int(target_tx.get('value', 0))
        if target_value < 10**18:
            return None
        
        front_run_value = target_value // 3
        
        front_run_tx = {
            'from': self.account.address,
            'to': target_tx['to'],
            'value': front_run_value,
            'gas': 200000,
            'maxFeePerGas': int(target_tx.get('maxFeePerGas', self.w3.eth.gas_price)) + 1,
            'maxPriorityFeePerGas': int(target_tx.get('maxPriorityFeePerGas', 2 * 10**9)) + 1,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'chainId': 1
        }
        
        back_run_tx = {
            'from': self.account.address,
            'to': target_tx['to'],
            'value': 0,
            'gas': 200000,
            'maxFeePerGas': int(target_tx.get('maxFeePerGas', self.w3.eth.gas_price)) - 1,
            'maxPriorityFeePerGas': int(target_tx.get('maxPriorityFeePerGas', 2 * 10**9)) - 1,
            'nonce': self.w3.eth.get_transaction_count(self.account.address) + 1,
            'chainId': 1
        }
        
        signed_front = self.account.sign_transaction(front_run_tx)
        signed_back = self.account.sign_transaction(back_run_tx)
        
        return [signed_front.rawTransaction.hex(), target_tx['hash'], signed_back.rawTransaction.hex()]
    
    def execute_flash_loan(self, amount, asset):
        aave_pool = self.w3.eth.contract(
            address='0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2',
            abi=[{"inputs":[{"name":"receiverAddress","type":"address"},{"name":"asset","type":"address"},{"name":"amount","type":"uint256"},{"name":"params","type":"bytes"},{"name":"referralCode","type":"uint16"}],"name":"flashLoanSimple","outputs":[],"stateMutability":"nonpayable","type":"function"}]
        )
        
        params = Web3.to_bytes(hexstr='0x')
        
        tx = aave_pool.functions.flashLoanSimple(
            self.account.address,
            asset,
            amount,
            params,
            0
        ).build_transaction({
            'from': self.account.address,
            'gas': 500000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'chainId': 1
        })
        
        return tx
    
    async def monitor_mempool(self):
        print("Monitoring mempool for opportunities...")
        
        while True:
            try:
                pending_filter = self.w3.eth.filter('pending')
                pending_txs = pending_filter.get_new_entries()
                
                for tx_hash in pending_txs[:10]:
                    try:
                        tx = self.w3.eth.get_transaction(tx_hash)
                        
                        if tx and tx.get('to'):
                            if tx['to'] in ['0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D', '0xE592427A0AEce92De3Edee1F18E0157C05861564']:
                                if tx.get('value', 0) > 10**18:
                                    print(f"Found large swap: {tx['hash'].hex()}, value: {tx['value'] / 10**18:.2f} ETH")
                    except:
                        continue
                
                await asyncio.sleep(1)
                
            except Exception as e:
                await asyncio.sleep(5)
    
    async def run(self):
        print(f"MEV Bot Started")
        print(f"Account: {self.account.address}")
        print(f"Balance: {self.w3.eth.get_balance(self.account.address) / 10**18:.4f} ETH")
        print(f"Current block: {self.w3.eth.block_number}")
        print(f"Gas price: {self.w3.eth.gas_price / 10**9:.2f} gwei")
        
        while True:
            try:
                opportunities = self.find_arbitrage()
                if opportunities:
                    print(f"\nFound {len(opportunities)} arbitrage opportunities:")
                    for opp in opportunities:
                        print(f"  {opp['dex1']} vs {opp['dex2']}: {opp['price_diff_pct']:.3f}% difference")
                        print(f"  Estimated profit: ${opp['estimated_profit']:.2f}")
                
                liquidatable = self.check_liquidations()
                if liquidatable:
                    print(f"\nFound {len(liquidatable)} liquidatable positions:")
                    for pos in liquidatable:
                        print(f"  User: {pos['user'][:10]}...")
                        print(f"  Health factor: {pos['health_factor']:.3f}")
                        print(f"  Max liquidation: {pos['max_liquidation']:.2f} ETH")
                
                await asyncio.sleep(12)
                
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(12)

if __name__ == "__main__":
    bot = RealMEVBot()
    asyncio.run(bot.run())
