import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Tuple
import asyncio
from collections import deque
import time

class LiquidationLSTM(nn.Module):
    def __init__(self, input_size=128, hidden_size=256, num_layers=4, output_size=3):
        super().__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2,
            bidirectional=True
        )
        
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_size * 2,
            num_heads=8,
            dropout=0.1
        )
        
        self.feature_extractor = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        self.liquidation_predictor = nn.Linear(hidden_size // 2, 1)
        self.block_predictor = nn.Linear(hidden_size // 2, 1)
        self.profit_predictor = nn.Linear(hidden_size // 2, 1)
        
        self.sigmoid = nn.Sigmoid()
        
    def forward(self, x, hidden=None):
        batch_size, seq_len, _ = x.shape
        
        if hidden is None:
            h0 = torch.zeros(self.num_layers * 2, batch_size, self.hidden_size).to(x.device)
            c0 = torch.zeros(self.num_layers * 2, batch_size, self.hidden_size).to(x.device)
            hidden = (h0, c0)
        
        lstm_out, hidden = self.lstm(x, hidden)
        
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        
        features = self.feature_extractor(attn_out[:, -1, :])
        
        liquidation_prob = self.sigmoid(self.liquidation_predictor(features))
        blocks_until = self.block_predictor(features)
        expected_profit = self.profit_predictor(features) * 1000000
        
        return liquidation_prob, blocks_until, expected_profit, hidden

class AdvancedLiquidationPredictor:
    def __init__(self):
        self.model = LiquidationLSTM()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        self.position_history = {}
        self.liquidation_history = deque(maxlen=10000)
        self.prediction_cache = {}
        
        self.protocol_configs = {
            'aave_v3': {
                'address': '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2',
                'liquidation_threshold': 0.85,
                'liquidation_bonus': 0.05,
                'health_factor_threshold': 1.0
            },
            'compound_v3': {
                'address': '0xc3d688B66703497DAA19211EEdff47f25384cdc3',
                'liquidation_threshold': 0.83,
                'liquidation_bonus': 0.08,
                'health_factor_threshold': 1.0
            },
            'maker': {
                'address': '0x60744434d6339a6B27d73d9Eda62b6F66a0a04FA',
                'liquidation_threshold': 0.77,
                'liquidation_bonus': 0.13,
                'health_factor_threshold': 1.0
            },
            'morpho': {
                'address': '0x8888882f8f843896699869179fB6E4f7e3B58888',
                'liquidation_threshold': 0.87,
                'liquidation_bonus': 0.045,
                'health_factor_threshold': 1.0
            }
        }
        
        self.oracle_feeds = {}
        self.price_history = {}
        
    async def load_trained_model(self):
        try:
            checkpoint = torch.load('models/liquidation_lstm_v3.pth', map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.eval()
            print("Loaded pre-trained liquidation model")
        except:
            self.train_on_historical_data()
    
    def train_on_historical_data(self):
        training_data = self.load_historical_liquidations()
        
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        criterion = nn.BCELoss()
        
        self.model.train()
        
        for epoch in range(100):
            total_loss = 0
            
            for batch in self.create_batches(training_data, batch_size=32):
                features, labels = self.prepare_training_batch(batch)
                
                features = torch.FloatTensor(features).to(self.device)
                labels = torch.FloatTensor(labels).to(self.device)
                
                optimizer.zero_grad()
                
                liquidation_prob, blocks_pred, profit_pred, _ = self.model(features)
                
                loss = criterion(liquidation_prob.squeeze(), labels[:, 0])
                loss += nn.MSELoss()(blocks_pred.squeeze(), labels[:, 1])
                loss += nn.MSELoss()(profit_pred.squeeze(), labels[:, 2])
                
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
        
        self.model.eval()
        torch.save({
            'model_state_dict': self.model.state_dict()
        }, 'models/liquidation_lstm_v3.pth')
    
    async def scan_all_positions(self) -> List[Dict]:
        at_risk_positions = []
        
        for protocol_name, config in self.protocol_configs.items():
            positions = await self.get_protocol_positions(protocol_name, config['address'])
            
            for position in positions:
                features = self.extract_position_features(position)
                
                with torch.no_grad():
                    features_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)
                    
                    liquidation_prob, blocks_until, expected_profit, _ = self.model(features_tensor)
                    
                    liquidation_prob = liquidation_prob.item()
                    blocks_until = max(1, int(blocks_until.item()))
                    expected_profit = expected_profit.item()
                
                if liquidation_prob > 0.7:
                    at_risk_positions.append({
                        'protocol': protocol_name,
                        'user': position['user'],
                        'position_id': position['id'],
                        'health_factor': position['health_factor'],
                        'collateral': position['collateral'],
                        'debt': position['debt'],
                        'liquidation_probability': liquidation_prob,
                        'blocks_until_liquidation': blocks_until,
                        'expected_profit': expected_profit,
                        'optimal_liquidation_amount': self.calculate_optimal_liquidation(position),
                        'gas_optimized_calldata': self.generate_liquidation_calldata(position)
                    })
        
        return sorted(at_risk_positions, key=lambda x: x['expected_profit'], reverse=True)
    
    async def predict_liquidation_cascade(self, initial_liquidation: Dict) -> List[Dict]:
        cascade_predictions = []
        
        collateral_asset = initial_liquidation['collateral']['asset']
        liquidation_amount = initial_liquidation['collateral']['amount']
        
        price_impact = self.estimate_price_impact(collateral_asset, liquidation_amount)
        
        new_price = self.get_current_price(collateral_asset) * (1 - price_impact)
        
        for protocol_name, config in self.protocol_configs.items():
            positions = await self.get_positions_with_collateral(protocol_name, collateral_asset)
            
            for position in positions:
                new_health = self.recalculate_health_factor(position, collateral_asset, new_price)
                
                if new_health < config['health_factor_threshold']:
                    cascade_predictions.append({
                        'protocol': protocol_name,
                        'position': position,
                        'new_health_factor': new_health,
                        'triggered_by': initial_liquidation['position_id'],
                        'expected_block': initial_liquidation['blocks_until_liquidation'] + 1
                    })
        
        return cascade_predictions
    
    def extract_position_features(self, position: Dict) -> np.ndarray:
        features = np.zeros(128)
        
        features[0] = position['health_factor']
        features[1] = position['collateral']['amount'] / 10**18
        features[2] = position['debt']['amount'] / 10**18
        features[3] = position['collateral']['value_usd'] / position['debt']['value_usd'] if position['debt']['value_usd'] > 0 else 0
        
        collateral_volatility = self.get_asset_volatility(position['collateral']['asset'])
        features[4] = collateral_volatility
        
        debt_volatility = self.get_asset_volatility(position['debt']['asset'])
        features[5] = debt_volatility
        
        features[6:26] = self.get_price_history_features(position['collateral']['asset'])
        features[26:46] = self.get_price_history_features(position['debt']['asset'])
        
        features[46] = self.get_protocol_utilization(position['protocol'])
        features[47] = self.get_gas_price() / 10**9
        
        features[48:68] = self.get_market_conditions()
        
        features[68:88] = self.get_user_history(position['user'])
        
        features[88:108] = self.get_correlated_assets_features(position)
        
        features[108:128] = self.get_defi_tvl_trends()
        
        return features
    
    async def monitor_real_time(self):
        while True:
            positions = await self.scan_all_positions()
            
            for position in positions[:10]:
                if position['liquidation_probability'] > 0.9:
                    await self.prepare_liquidation_execution(position)
                elif position['liquidation_probability'] > 0.8:
                    await self.monitor_closely(position)
            
            await asyncio.sleep(1)
    
    async def prepare_liquidation_execution(self, position: Dict) -> Dict:
        flash_loan_amount = position['debt']['amount']
        
        flash_loan_params = self.get_optimal_flash_loan(flash_loan_amount)
        
        liquidation_calldata = self.generate_liquidation_calldata(position)
        
        gas_price = self.calculate_competitive_gas_price(position['expected_profit'])
        
        bundle = self.create_liquidation_bundle(
            flash_loan_params,
            liquidation_calldata,
            gas_price
        )
        
        return {
            'position': position,
            'bundle': bundle,
            'expected_execution_block': position['blocks_until_liquidation'],
            'backup_strategies': self.generate_backup_strategies(position)
        }
    
    def calculate_optimal_liquidation(self, position: Dict) -> Dict:
        max_liquidation = position['debt']['amount'] * 0.5
        
        liquidation_bonus = self.protocol_configs[position['protocol']]['liquidation_bonus']
        
        collateral_to_receive = max_liquidation * (1 + liquidation_bonus)
        
        slippage_threshold = 0.02
        
        optimal_chunks = self.calculate_liquidation_chunks(
            max_liquidation,
            position['collateral']['liquidity'],
            slippage_threshold
        )
        
        return {
            'total_amount': max_liquidation,
            'chunks': optimal_chunks,
            'expected_collateral': collateral_to_receive,
            'expected_profit': collateral_to_receive * 0.98 - max_liquidation
        }
    
    def generate_liquidation_calldata(self, position: Dict) -> str:
        protocol = position['protocol']
        
        if protocol == 'aave_v3':
            return self.encode_aave_liquidation(position)
        elif protocol == 'compound_v3':
            return self.encode_compound_liquidation(position)
        elif protocol == 'maker':
            return self.encode_maker_liquidation(position)
        else:
            return self.encode_generic_liquidation(position)
    
    def encode_aave_liquidation(self, position: Dict) -> str:
        function_sig = '0x00a718a9'
        
        collateral_asset = position['collateral']['asset'].replace('0x', '').rjust(64, '0')
        debt_asset = position['debt']['asset'].replace('0x', '').rjust(64, '0')
        user = position['user'].replace('0x', '').rjust(64, '0')
        debt_to_cover = hex(position['optimal_liquidation_amount']['total_amount'])[2:].rjust(64, '0')
        receive_atoken = '0000000000000000000000000000000000000000000000000000000000000000'
        
        return function_sig + collateral_asset + debt_asset + user + debt_to_cover + receive_atoken
    
    async def get_protocol_positions(self, protocol: str, address: str) -> List[Dict]:
        positions = []
        
        if protocol == 'aave_v3':
            users = await self.get_aave_users(address)
            for user in users:
                position = await self.get_aave_position(address, user)
                if position['health_factor'] < 1.5:
                    positions.append(position)
        
        return positions
    
    async def get_aave_position(self, protocol_address: str, user: str) -> Dict:
        from web3 import Web3
        
        w3 = Web3(Web3.HTTPProvider('https://eth-mainnet.g.alchemy.com/v2/KEY'))
        
        pool = w3.eth.contract(
            address=protocol_address,
            abi=[{
                "name": "getUserAccountData",
                "type": "function",
                "inputs": [{"name": "user", "type": "address"}],
                "outputs": [
                    {"name": "totalCollateralETH", "type": "uint256"},
                    {"name": "totalDebtETH", "type": "uint256"},
                    {"name": "availableBorrowsETH", "type": "uint256"},
                    {"name": "currentLiquidationThreshold", "type": "uint256"},
                    {"name": "ltv", "type": "uint256"},
                    {"name": "healthFactor", "type": "uint256"}
                ]
            }]
        )
        
        data = pool.functions.getUserAccountData(user).call()
        
        return {
            'protocol': 'aave_v3',
            'user': user,
            'id': f"aave_{user}_{int(time.time())}",
            'collateral': {
                'amount': data[0],
                'asset': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
                'value_usd': data[0] * 3200 / 10**18,
                'liquidity': 100000000 * 10**18
            },
            'debt': {
                'amount': data[1],
                'asset': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
                'value_usd': data[1] / 10**6
            },
            'health_factor': data[5] / 10**18
        }
    
    def get_asset_volatility(self, asset: str) -> float:
        volatilities = {
            '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2': 0.02,
            '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48': 0.001,
            '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599': 0.025
        }
        return volatilities.get(asset, 0.03)
    
    def get_price_history_features(self, asset: str) -> np.ndarray:
        features = np.zeros(20)
        
        features[0] = 3200 if asset == '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2' else 1
        features[1] = np.random.uniform(-0.05, 0.05)
        features[2] = np.random.uniform(-0.1, 0.1)
        features[3:20] = np.random.randn(17) * 0.01
        
        return features
    
    def load_historical_liquidations(self) -> List[Dict]:
        return [
            {
                'features': np.random.randn(100, 128),
                'liquidated': 1,
                'blocks_until': np.random.randint(1, 100),
                'profit': np.random.uniform(1000, 100000)
            }
            for _ in range(1000)
        ]
    
    def create_batches(self, data: List, batch_size: int):
        for i in range(0, len(data), batch_size):
            yield data[i:i + batch_size]
    
    def prepare_training_batch(self, batch: List) -> Tuple[np.ndarray, np.ndarray]:
        features = np.array([item['features'] for item in batch])
        labels = np.array([
            [item['liquidated'], item['blocks_until'], item['profit']]
            for item in batch
        ])
        return features, labels