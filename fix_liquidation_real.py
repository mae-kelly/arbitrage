import json
from web3 import Web3

def get_real_volatility_code():
    return """
    async def get_real_asset_volatility(self, asset: str) -> float:
        '''Calculate real volatility from price history'''
        try:
            # Get price oracle
            oracle_address = {
                '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2': '0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419',  # ETH/USD
                '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48': '0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6',  # USDC/USD
                '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599': '0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c',  # BTC/USD
            }.get(asset)
            
            if not oracle_address:
                return 0.03  # Default volatility
            
            oracle = self.w3.eth.contract(
                address=oracle_address,
                abi=[{"inputs":[],"name":"latestRoundData","outputs":[{"name":"roundId","type":"uint80"},{"name":"answer","type":"int256"},{"name":"startedAt","type":"uint256"},{"name":"updatedAt","type":"uint256"},{"name":"answeredInRound","type":"uint80"}],"type":"function"},
                     {"inputs":[{"name":"_roundId","type":"uint80"}],"name":"getRoundData","outputs":[{"name":"roundId","type":"uint80"},{"name":"answer","type":"int256"},{"name":"startedAt","type":"uint256"},{"name":"updatedAt","type":"uint256"},{"name":"answeredInRound","type":"uint80"}],"type":"function"}]
            )
            
            # Get last 20 rounds of price data
            latest_round = oracle.functions.latestRoundData().call()
            current_round_id = latest_round[0]
            
            prices = []
            for i in range(20):
                try:
                    round_data = oracle.functions.getRoundData(current_round_id - i).call()
                    prices.append(round_data[1] / 10**8)
                except:
                    break
            
            if len(prices) < 2:
                return 0.03
            
            # Calculate returns
            returns = []
            for i in range(1, len(prices)):
                ret = (prices[i-1] - prices[i]) / prices[i]
                returns.append(ret)
            
            # Calculate volatility (standard deviation of returns)
            import numpy as np
            volatility = np.std(returns) * np.sqrt(365)  # Annualized
            
            return min(max(volatility, 0.001), 0.5)  # Cap between 0.1% and 50%
            
        except Exception as e:
            print(f"Error calculating volatility: {e}")
            return 0.03
    """

# Update the file
with open('liquidation_predictor_ml.py', 'r') as f:
    content = f.read()

# Replace the mock function
content = content.replace(
    "def get_asset_volatility(self, asset: str) -> float:",
    get_real_volatility_code() + "\n    def get_asset_volatility_old(self, asset: str) -> float:"
)

with open('liquidation_predictor_ml.py', 'w') as f:
    f.write(content)
