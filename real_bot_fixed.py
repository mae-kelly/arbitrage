from web3 import Web3
import json
import asyncio
import time
from eth_account import Account

class RealMEVBot:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider('https://rpc.flashbots.net'))
        if not self.w3.is_connected():
            self.w3 = Web3(Web3.HTTPProvider('https://eth.llamarpc.com'))
        
        with open('.keys.json', 'r') as f:
            keys = json.load(f)
            self.account = Account.from_key(keys['main']['private_key'])
        
        self.contracts = {
            'uniswap_v2_router': '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
            'uniswap_v2_factory': '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f',
            'sushiswap_factory': '0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac',
            'aave_v3': '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2',
            'balancer': '0xBA12222222228d8Ba445958a75a0704d566BF2C8'
        }
        
        self.tokens = {
            'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
            'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
            'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F'
        }
    
    def get_pair_address(self, factory, token0, token1):
        contract = self.w3.eth.contract(
            address=factory,
            abi=[{"inputs":[{"type":"address"},{"type":"address"}],"name":"getPair","outputs":[{"type":"address"}],"type":"function"}]
        )
        return contract.functions.getPair(token0, token1).call()
    
    def get_reserves(self, pair):
        contract = self.w3.eth.contract(
            address=pair,
            abi=[{"inputs":[],"name":"getReserves","outputs":[{"type":"uint112"},{"type":"uint112"},{"type":"uint32"}],"type":"function"},
                 {"inputs":[],"name":"token0","outputs":[{"type":"address"}],"type":"function"}]
        )
        reserves = contract.functions.getReserves().call()
        token0 = contract.functions.token0().call()
        return reserves, token0
    
    def calculate_price(self, pair, token_in, token_out):
        reserves, token0 = self.get_reserves(pair)
        
        if token0.lower() == token_in.lower():
            reserve_in = reserves[0]
            reserve_out = reserves[1]
        else:
            reserve_in = reserves[1]
            reserve_out = reserves[0]
        
        decimals_in = 18 if token_in == self.tokens['WETH'] else 6
        decimals_out = 6 if token_out == self.tokens['USDC'] or token_out == self.tokens['USDT'] else 18
        
        amount_in = 10 ** decimals_in
        amount_out = self.get_amount_out(amount_in, reserve_in, reserve_out)
        
        price = amount_out / (10 ** decimals_out)
        
        return price
    
    def get_amount_out(self, amount_in, reserve_in, reserve_out):
        amount_in_with_fee = amount_in * 997
        numerator = amount_in_with_fee * reserve_out
        denominator = (reserve_in * 1000) + amount_in_with_fee
        return numerator // denominator
    
    def find_arbitrage_opportunities(self):
        opportunities = []
        
        uni_pair = self.get_pair_address(
            self.contracts['uniswap_v2_factory'],
            self.tokens['WETH'],
            self.tokens['USDC']
        )
        
        sushi_pair = self.get_pair_address(
            self.contracts['sushiswap_factory'],
            self.tokens['WETH'],
            self.tokens['USDC']
        )
        
        if uni_pair != '0x0000000000000000000000000000000000000000':
            uni_price = self.calculate_price(uni_pair, self.tokens['WETH'], self.tokens['USDC'])
            
            if sushi_pair != '0x0000000000000000000000000000000000000000':
                sushi_price = self.calculate_price(sushi_pair, self.tokens['WETH'], self.tokens['USDC'])
                
                price_diff = abs(uni_price - sushi_price)
                price_diff_pct = (price_diff / min(uni_price, sushi_price)) * 100 if min(uni_price, sushi_price) > 0 else 0
                
                if price_diff_pct > 0.1:
                    opportunities.append({
                        'type': 'arbitrage',
                        'pair': 'WETH/USDC',
                        'uniswap_price': uni_price,
                        'sushiswap_price': sushi_price,
                        'difference_pct': price_diff_pct,
                        'profit_per_eth': price_diff
                    })
        
        return opportunities
    
    def check_pending_transactions(self):
        sandwich_targets = []
        
        pending_block = self.w3.eth.get_block('pending', full_transactions=True)
        
        for tx in pending_block.transactions[:20]:
            if tx.to and tx.to.lower() in [self.contracts['uniswap_v2_router'].lower()]:
                if tx.value > 5 * 10**18:
                    sandwich_targets.append({
                        'hash': tx.hash.hex(),
                        'from': tx['from'],
                        'value_eth': tx.value / 10**18,
                        'gas_price': tx.gasPrice / 10**9
                    })
        
        return sandwich_targets
    
    def calculate_sandwich_profit(self, target_tx_value):
        front_run_amount = target_tx_value * 0.3
        
        price_impact = (front_run_amount / (100 * 10**18)) ** 0.5
        
        expected_profit = front_run_amount * price_impact * 0.5
        
        gas_cost = 300000 * 30 * 10**9
        
        net_profit = expected_profit - gas_cost
        
        return net_profit / 10**18
    
    def get_flash_loan_availability(self):
        aave = self.w3.eth.contract(
            address=self.contracts['aave_v3'],
            abi=[{"inputs":[{"type":"address"}],"name":"getReserveData","outputs":[{"components":[{"type":"uint256"},{"type":"uint128"},{"type":"uint128"},{"type":"uint128"},{"type":"uint128"},{"type":"uint128"},{"type":"uint40"},{"type":"uint16"},{"type":"address"},{"type":"address"},{"type":"address"},{"type":"address"},{"type":"uint128"},{"type":"uint128"},{"type":"uint128"}],"type":"tuple"}],"type":"function"}]
        )
        
        try:
            usdc_data = aave.functions.getReserveData(self.tokens['USDC']).call()
            available_liquidity = usdc_data[2] / 10**6
            return available_liquidity
        except:
            return 0
    
    async def run(self):
        print(f"MEV Bot Active")
        print(f"Wallet: {self.account.address}")
        print(f"Network: Ethereum Mainnet")
        print(f"Block: {self.w3.eth.block_number:,}")
        print("-" * 50)
        
        while True:
            try:
                opportunities = self.find_arbitrage_opportunities()
                
                if opportunities:
                    for opp in opportunities:
                        print(f"\n💰 ARBITRAGE FOUND")
                        print(f"   Uniswap: ${opp['uniswap_price']:.2f}")
                        print(f"   Sushiswap: ${opp['sushiswap_price']:.2f}")
                        print(f"   Difference: {opp['difference_pct']:.3f}%")
                        print(f"   Profit/ETH: ${opp['profit_per_eth']:.2f}")
                
                sandwich_targets = self.check_pending_transactions()
                
                if sandwich_targets:
                    for target in sandwich_targets:
                        profit = self.calculate_sandwich_profit(target['value_eth'] * 10**18)
                        if profit > 0:
                            print(f"\n🥪 SANDWICH TARGET")
                            print(f"   TX: {target['hash'][:10]}...")
                            print(f"   Value: {target['value_eth']:.2f} ETH")
                            print(f"   Est Profit: {profit:.4f} ETH")
                
                flash_liquidity = self.get_flash_loan_availability()
                if flash_liquidity > 0:
                    print(f"\n💸 Flash Loan Available: ${flash_liquidity:,.0f}")
                
                await asyncio.sleep(12)
                
            except Exception as e:
                await asyncio.sleep(12)

if __name__ == "__main__":
    bot = RealMEVBot()
    asyncio.run(bot.run())
