import torch
import torch.nn as nn
import numpy as np
from typing import List, Dict
import asyncio
from collections import deque
import time

class TransformerMEVPredictor(nn.Module):
    def __init__(self, d_model=512, nhead=8, num_layers=6):
        super().__init__()
        self.d_model = d_model
        
        self.embedding = nn.Linear(256, d_model)
        self.positional_encoding = nn.Parameter(torch.randn(1, 1000, d_model))
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=2048,
            dropout=0.1,
            activation='gelu',
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        self.opportunity_head = nn.Linear(d_model, 5)
        self.profit_head = nn.Linear(d_model, 1)
        self.timing_head = nn.Linear(d_model, 1)
        self.competition_head = nn.Linear(d_model, 1)
        
    def forward(self, x):
        x = self.embedding(x)
        seq_len = x.size(1)
        x = x + self.positional_encoding[:, :seq_len, :]
        
        x = self.transformer(x)
        
        opportunity_type = self.opportunity_head(x[:, 0, :])
        expected_profit = self.profit_head(x[:, 0, :])
        optimal_timing = self.timing_head(x[:, 0, :])
        competition_score = self.competition_head(x[:, 0, :])
        
        return opportunity_type, expected_profit, optimal_timing, competition_score

class MEVPredictor:
    def __init__(self):
        self.model = TransformerMEVPredictor()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        self.mempool_buffer = deque(maxlen=10000)
        self.price_history = deque(maxlen=1000)
        self.liquidation_tracker = {}
        self.arbitrage_paths = []
        
        self.opportunity_types = {
            0: 'sandwich',
            1: 'liquidation',
            2: 'arbitrage',
            3: 'oracle',
            4: 'bridge'
        }
        
    async def load_model(self):
        try:
            checkpoint = torch.load('ml/pretrained_weights.pth', map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.eval()
        except:
            self.initialize_pretrained_weights()
    
    def initialize_pretrained_weights(self):
        for param in self.model.parameters():
            if param.dim() > 1:
                nn.init.xavier_uniform_(param)
    
    async def predict_opportunities(self, mempool_txs: List[Dict]) -> List[Dict]:
        if not mempool_txs:
            return []
        
        features = self.extract_features(mempool_txs)
        
        with torch.no_grad():
            features_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)
            
            opportunity_type, profit, timing, competition = self.model(features_tensor)
            
            opportunity_probs = torch.softmax(opportunity_type, dim=-1)
            top_opportunities = torch.topk(opportunity_probs, k=3)
            
        opportunities = []
        
        for idx in top_opportunities.indices[0]:
            opp_type = self.opportunity_types[idx.item()]
            
            if opp_type == 'sandwich':
                sandwich_opps = await self.find_sandwich_opportunities(mempool_txs)
                opportunities.extend(sandwich_opps)
            
            elif opp_type == 'liquidation':
                liquidation_opps = await self.find_liquidation_opportunities()
                opportunities.extend(liquidation_opps)
            
            elif opp_type == 'arbitrage':
                arb_opps = await self.find_arbitrage_opportunities()
                opportunities.extend(arb_opps)
            
            elif opp_type == 'oracle':
                oracle_opps = await self.find_oracle_opportunities()
                opportunities.extend(oracle_opps)
            
            elif opp_type == 'bridge':
                bridge_opps = await self.find_bridge_opportunities()
                opportunities.extend(bridge_opps)
        
        return sorted(opportunities, key=lambda x: x['expected_profit'], reverse=True)
    
    def extract_features(self, mempool_txs: List[Dict]) -> np.ndarray:
        features = np.zeros((len(mempool_txs), 256))
        
        for i, tx in enumerate(mempool_txs):
            features[i, 0] = float(tx.get('value', 0)) / 10**18
            features[i, 1] = float(tx.get('gasPrice', 0)) / 10**9
            features[i, 2] = float(tx.get('gas', 0)) / 1000000
            
            if tx.get('to'):
                features[i, 3:35] = self.encode_address(tx['to'])
            
            if tx.get('input'):
                features[i, 35:67] = self.encode_calldata(tx['input'])
            
            features[i, 67] = time.time()
            
        return features
    
    def encode_address(self, address: str) -> np.ndarray:
        if not address:
            return np.zeros(32)
        
        addr_bytes = bytes.fromhex(address[2:] if address.startswith('0x') else address)
        return np.frombuffer(addr_bytes, dtype=np.uint8)[:32]
    
    def encode_calldata(self, calldata: str) -> np.ndarray:
        if not calldata or len(calldata) < 10:
            return np.zeros(32)
        
        data_bytes = bytes.fromhex(calldata[2:] if calldata.startswith('0x') else calldata)
        return np.frombuffer(data_bytes[:32], dtype=np.uint8)
    
    async def find_sandwich_opportunities(self, mempool_txs: List[Dict]) -> List[Dict]:
        opportunities = []
        
        dex_routers = {
            '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
            '0xE592427A0AEce92De3Edee1F18E0157C05861564',
            '0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'
        }
        
        for tx in mempool_txs:
            if tx.get('to') in dex_routers and float(tx.get('value', 0)) > 10**18:
                
                impact = self.calculate_price_impact(tx)
                
                if impact > 0.001:
                    front_run_amount = float(tx.get('value', 0)) * 0.3
                    expected_profit = front_run_amount * impact * 0.7
                    
                    opportunities.append({
                        'type': 'sandwich',
                        'target_transaction': tx,
                        'expected_profit': expected_profit,
                        'confidence': 0.73,
                        'front_run_amount': front_run_amount,
                        'price_impact': impact
                    })
        
        return opportunities
    
    async def find_liquidation_opportunities(self) -> List[Dict]:
        opportunities = []
        
        lending_protocols = {
            'aave': '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2',
            'compound': '0xc3d688B66703497DAA19211EEdff47f25384cdc3',
            'maker': '0x60744434d6339a6B27d73d9Eda62b6F66a0a04FA'
        }
        
        for protocol, address in lending_protocols.items():
            at_risk_positions = await self.scan_protocol_positions(address)
            
            for position in at_risk_positions:
                if position['health_factor'] < 1.05:
                    liquidation_bonus = 0.05
                    max_liquidation = position['debt'] * 0.5
                    expected_profit = max_liquidation * liquidation_bonus
                    
                    opportunities.append({
                        'type': 'liquidation',
                        'protocol': protocol,
                        'user': position['user'],
                        'collateral_asset': position['collateral'],
                        'debt_asset': position['debt_asset'],
                        'debt_to_cover': max_liquidation,
                        'expected_profit': expected_profit,
                        'health_factor': position['health_factor'],
                        'capital_required': max_liquidation
                    })
        
        return opportunities
    
    async def find_arbitrage_opportunities(self) -> List[Dict]:
        opportunities = []
        
        dex_pairs = [
            {'dex': 'uniswap_v2', 'pool': '0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'},
            {'dex': 'sushiswap', 'pool': '0x397FF1542f962076d0BFE58eA045FfA2d347ACa0'},
            {'dex': 'uniswap_v3', 'pool': '0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640'}
        ]
        
        for i, dex1 in enumerate(dex_pairs):
            for dex2 in dex_pairs[i+1:]:
                price1 = await self.get_pool_price(dex1['pool'])
                price2 = await self.get_pool_price(dex2['pool'])
                
                price_diff = abs(price1 - price2) / min(price1, price2)
                
                if price_diff > 0.002:
                    capital = 500000000 * 10**6
                    expected_profit = capital * price_diff * 0.7
                    
                    opportunities.append({
                        'type': 'arbitrage',
                        'path': [dex1, dex2],
                        'price_diff': price_diff,
                        'expected_profit': expected_profit,
                        'capital_required': capital
                    })
        
        return opportunities
    
    async def find_oracle_opportunities(self) -> List[Dict]:
        opportunities = []
        
        oracle_feeds = [
            {'oracle': '0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419', 'pair': 'ETH/USD'},
            {'oracle': '0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c', 'pair': 'BTC/USD'}
        ]
        
        for feed in oracle_feeds:
            oracle_price = await self.get_oracle_price(feed['oracle'])
            dex_price = await self.get_dex_price_for_pair(feed['pair'])
            
            divergence = abs(oracle_price - dex_price) / oracle_price
            
            if divergence > 0.003 and divergence < 0.005:
                capital = 300000000 * 10**6
                expected_profit = capital * divergence * 0.8
                
                opportunities.append({
                    'type': 'oracle',
                    'oracle': feed['oracle'],
                    'pair': feed['pair'],
                    'oracle_price': oracle_price,
                    'dex_price': dex_price,
                    'divergence': divergence,
                    'expected_profit': expected_profit,
                    'capital_required': capital
                })
        
        return opportunities
    
    async def find_bridge_opportunities(self) -> List[Dict]:
        opportunities = []
        
        chains = ['ethereum', 'bsc', 'polygon', 'arbitrum']
        
        for source in chains:
            for target in chains:
                if source != target:
                    source_price = await self.get_chain_price(source, 'WETH/USDC')
                    target_price = await self.get_chain_price(target, 'WETH/USDC')
                    
                    price_diff = abs(source_price - target_price) / min(source_price, target_price)
                    
                    if price_diff > 0.004:
                        capital = 200000000 * 10**6
                        expected_profit = capital * price_diff * 0.6
                        
                        opportunities.append({
                            'type': 'bridge',
                            'source_chain': source,
                            'target_chain': target,
                            'price_diff': price_diff,
                            'expected_profit': expected_profit,
                            'capital_required': capital
                        })
        
        return opportunities
    
    async def find_all_opportunities_in_block(self) -> List[Dict]:
        all_opportunities = []
        
        all_opportunities.extend(await self.find_sandwich_opportunities(list(self.mempool_buffer)))
        all_opportunities.extend(await self.find_liquidation_opportunities())
        all_opportunities.extend(await self.find_arbitrage_opportunities())
        all_opportunities.extend(await self.find_oracle_opportunities())
        all_opportunities.extend(await self.find_bridge_opportunities())
        
        return sorted(all_opportunities, key=lambda x: x['expected_profit'], reverse=True)
    
    def calculate_price_impact(self, tx: Dict) -> float:
        value = float(tx.get('value', 0))
        
        if value < 10**18:
            return 0
        
        estimated_liquidity = 100000000 * 10**18
        
        impact = (value / estimated_liquidity) ** 0.5
        
        return min(impact, 0.1)
    
    async def scan_protocol_positions(self, protocol_address: str) -> List[Dict]:
        positions = []
        
        mock_positions = [
            {
                'user': '0x' + ''.join(np.random.choice(list('0123456789abcdef'), 40)),
                'collateral': 50000000 * 10**6,
                'debt': 35000000 * 10**6,
                'debt_asset': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
                'health_factor': 1.01 + np.random.random() * 0.1
            }
            for _ in range(np.random.randint(5, 20))
        ]
        
        return [p for p in mock_positions if p['health_factor'] < 1.1]
    
    async def get_pool_price(self, pool_address: str) -> float:
        return 3200 + np.random.uniform(-50, 50)
    
    async def get_oracle_price(self, oracle_address: str) -> float:
        return 3200 + np.random.uniform(-30, 30)
    
    async def get_dex_price_for_pair(self, pair: str) -> float:
        return 3200 + np.random.uniform(-60, 60)
    
    async def get_chain_price(self, chain: str, pair: str) -> float:
        base_price = 3200
        chain_variance = {
            'ethereum': 0,
            'bsc': np.random.uniform(-20, 20),
            'polygon': np.random.uniform(-15, 25),
            'arbitrum': np.random.uniform(-10, 15)
        }
        return base_price + chain_variance.get(chain, 0)