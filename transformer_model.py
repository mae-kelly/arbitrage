import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple, List
import math

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, n_heads):
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads
        
        self.W_q = nn.Linear(d_model, d_model)
        self.W_k = nn.Linear(d_model, d_model)
        self.W_v = nn.Linear(d_model, d_model)
        self.W_o = nn.Linear(d_model, d_model)
        
    def forward(self, query, key, value, mask=None):
        batch_size = query.size(0)
        
        Q = self.W_q(query).view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        K = self.W_k(key).view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        V = self.W_v(value).view(batch_size, -1, self.n_heads, self.d_k).transpose(1, 2)
        
        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.d_k)
        
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
        
        attention = F.softmax(scores, dim=-1)
        context = torch.matmul(attention, V)
        
        context = context.transpose(1, 2).contiguous().view(batch_size, -1, self.d_model)
        output = self.W_o(context)
        
        return output

class TransformerBlock(nn.Module):
    def __init__(self, d_model, n_heads, d_ff, dropout):
        super().__init__()
        self.attention = MultiHeadAttention(d_model, n_heads)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        
        self.feed_forward = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model)
        )
        
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x, mask=None):
        attn_output = self.attention(x, x, x, mask)
        x = self.norm1(x + self.dropout(attn_output))
        
        ff_output = self.feed_forward(x)
        x = self.norm2(x + self.dropout(ff_output))
        
        return x

class MEVTransformer(nn.Module):
    def __init__(
        self,
        input_dim=1024,
        d_model=512,
        n_heads=16,
        n_layers=12,
        d_ff=2048,
        max_seq_length=10000,
        n_classes=5,
        dropout=0.1
    ):
        super().__init__()
        
        self.d_model = d_model
        self.input_projection = nn.Linear(input_dim, d_model)
        
        self.positional_encoding = nn.Parameter(torch.randn(1, max_seq_length, d_model))
        
        self.transformer_blocks = nn.ModuleList([
            TransformerBlock(d_model, n_heads, d_ff, dropout)
            for _ in range(n_layers)
        ])
        
        self.layer_norm = nn.LayerNorm(d_model)
        
        self.opportunity_classifier = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, n_classes)
        )
        
        self.profit_predictor = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, 1)
        )
        
        self.timing_predictor = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, 1)
        )
        
        self.confidence_predictor = nn.Sequential(
            nn.Linear(d_model, d_model // 4),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 4, 1),
            nn.Sigmoid()
        )
        
        self.competition_analyzer = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, 100)
        )
        
    def forward(self, x, mask=None):
        batch_size, seq_len, _ = x.shape
        
        x = self.input_projection(x)
        x = x + self.positional_encoding[:, :seq_len, :]
        
        for transformer in self.transformer_blocks:
            x = transformer(x, mask)
        
        x = self.layer_norm(x)
        
        pooled = x.mean(dim=1)
        
        opportunity_logits = self.opportunity_classifier(pooled)
        profit_prediction = self.profit_predictor(pooled)
        timing = self.timing_predictor(pooled)
        confidence = self.confidence_predictor(pooled)
        competition = self.competition_analyzer(pooled)
        
        return {
            'opportunity_type': opportunity_logits,
            'expected_profit': profit_prediction,
            'optimal_timing': timing,
            'confidence': confidence,
            'competition_analysis': competition
        }

class FeatureExtractor:
    def __init__(self):
        self.feature_dim = 1024
        
    def extract_transaction_features(self, tx: dict) -> np.ndarray:
        features = np.zeros(self.feature_dim)
        
        features[0] = float(tx.get('value', 0)) / 10**18
        features[1] = float(tx.get('gasPrice', 0)) / 10**9
        features[2] = float(tx.get('gas', 0)) / 1000000
        features[3] = float(tx.get('nonce', 0))
        
        if tx.get('to'):
            addr_bytes = bytes.fromhex(tx['to'][2:] if tx['to'].startswith('0x') else tx['to'])
            features[4:36] = np.frombuffer(addr_bytes, dtype=np.uint8) / 255.0
        
        if tx.get('from'):
            addr_bytes = bytes.fromhex(tx['from'][2:] if tx['from'].startswith('0x') else tx['from'])
            features[36:68] = np.frombuffer(addr_bytes, dtype=np.uint8) / 255.0
        
        if tx.get('input') and len(tx['input']) > 10:
            input_bytes = bytes.fromhex(tx['input'][2:] if tx['input'].startswith('0x') else tx['input'])
            features[68:580] = np.frombuffer(input_bytes[:512], dtype=np.uint8) / 255.0
        
        features[580:590] = self.extract_temporal_features()
        features[590:650] = self.extract_market_features()
        features[650:750] = self.extract_protocol_features(tx)
        features[750:850] = self.extract_cross_chain_features()
        features[850:950] = self.extract_competition_features()
        features[950:1024] = self.extract_historical_features()
        
        return features
    
    def extract_temporal_features(self) -> np.ndarray:
        features = np.zeros(10)
        current_time = np.datetime64('now')
        
        features[0] = current_time.astype(float) / 10**9
        features[1] = np.sin(2 * np.pi * features[0] / 86400)
        features[2] = np.cos(2 * np.pi * features[0] / 86400)
        features[3] = np.sin(2 * np.pi * features[0] / 604800)
        features[4] = np.cos(2 * np.pi * features[0] / 604800)
        
        return features
    
    def extract_market_features(self) -> np.ndarray:
        features = np.zeros(60)
        
        features[0] = 3200.0 / 10000
        features[1] = 67000.0 / 100000
        features[2] = 1.0
        features[3:10] = np.random.randn(7) * 0.1
        
        return features
    
    def extract_protocol_features(self, tx: dict) -> np.ndarray:
        features = np.zeros(100)
        
        protocol_addresses = {
            '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D': 0,
            '0xE592427A0AEce92De3Edee1F18E0157C05861564': 1,
            '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2': 2,
        }
        
        if tx.get('to') in protocol_addresses:
            features[protocol_addresses[tx['to']]] = 1.0
        
        return features
    
    def extract_cross_chain_features(self) -> np.ndarray:
        features = np.zeros(100)
        
        features[0] = 0.002
        features[1] = 0.0015
        features[2] = 0.0018
        features[3] = 0.0012
        
        return features
    
    def extract_competition_features(self) -> np.ndarray:
        features = np.zeros(100)
        
        features[0] = 1847 / 10000
        features[1] = 0.34
        features[2] = 0.67
        
        return features
    
    def extract_historical_features(self) -> np.ndarray:
        return np.random.randn(74) * 0.1

class MEVPredictionSystem:
    def __init__(self):
        self.model = MEVTransformer()
        self.feature_extractor = FeatureExtractor()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
    def predict(self, transactions: List[dict]) -> dict:
        features = []
        for tx in transactions:
            feat = self.feature_extractor.extract_transaction_features(tx)
            features.append(feat)
        
        features_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            predictions = self.model(features_tensor)
        
        opportunity_probs = F.softmax(predictions['opportunity_type'], dim=-1)
        
        return {
            'opportunity_type': opportunity_probs.cpu().numpy(),
            'expected_profit': predictions['expected_profit'].cpu().numpy(),
            'optimal_timing': predictions['optimal_timing'].cpu().numpy(),
            'confidence': predictions['confidence'].cpu().numpy(),
            'competition': predictions['competition_analysis'].cpu().numpy()
        }
    
    def save_model(self, path: str):
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'feature_extractor': self.feature_extractor,
        }, path)
    
    def load_model(self, path: str):
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.feature_extractor = checkpoint['feature_extractor']
        self.model.eval()