import os
from typing import Dict, List
from pydantic import BaseSettings

class Settings(BaseSettings):
   redis_host: str = "localhost"
   redis_port: int = 6379
   redis_db: int = 0
   log_level: str = "INFO"
   max_position_size: float = 0.02
   max_daily_loss: float = 0.05
   slippage_tolerance: float = 0.001
   
   class Config:
       env_file = ".env"

settings = Settings()

EXCHANGES = [
   "binance", "coinbase", "kraken", "bitfinex", "huobi", "okx", "kucoin",
   "bybit", "ftx", "gate", "mexc", "bitget", "cryptocom", "ascendex",
   "bingx", "bitmart", "bitrue", "bittrex", "bitvavo", "cex", "coinex",
   "digifinex", "exmo", "hitbtc", "lbank", "novadax", "okcoin", "phemex",
   "poloniex", "probit", "tidex", "wazirx", "whitebit", "xt", "yobit",
   "coincheck", "liquid", "zaif", "bitbank", "btcbox", "coinone", "korbit",
   "bithumb", "upbit", "bitflyer", "mercado", "braziliex", "foxbit", "ripio"
]

DEX_CONFIGS = {
   "ethereum": {
       "rpc_urls": [
           "https://eth-mainnet.alchemyapi.io/v2/YOUR_KEY",
           "https://mainnet.infura.io/v3/YOUR_KEY",
           "https://rpc.ankr.com/eth"
       ],
       "dexes": {
           "uniswap_v2": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
           "uniswap_v3": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
           "sushiswap": "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac"
       }
   },
   "bsc": {
       "rpc_urls": [
           "https://bsc-dataseed1.binance.org",
           "https://bsc-dataseed2.binance.org"
       ],
       "dexes": {
           "pancakeswap": "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"
       }
   },
   "polygon": {
       "rpc_urls": [
           "https://polygon-rpc.com",
           "https://rpc-mainnet.matic.network"
       ],
       "dexes": {
           "quickswap": "0x5757371414417b8C6CAad45bAeF941aBc7d3Ab32"
       }
   },
   "avalanche": {
       "rpc_urls": [
           "https://api.avax.network/ext/bc/C/rpc"
       ],
       "dexes": {
           "traderjoe": "0x9Ad6C38BE94206cA50bb0d90783181662f0Cfa10"
       }
   }
}

TRADING_PAIRS = [
   "BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "DOT/USDT",
   "XRP/USDT", "LTC/USDT", "LINK/USDT", "BCH/USDT", "UNI/USDT",
   "SOL/USDT", "MATIC/USDT", "AVAX/USDT", "ATOM/USDT", "ALGO/USDT"
]
