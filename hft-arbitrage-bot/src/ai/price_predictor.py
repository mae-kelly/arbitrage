import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import deque
import pandas as pd
from dataclasses import dataclass

@dataclass
class PredictionResult:
    symbol: str
    predicted_price: float
    confidence: float
    direction: str
    timeframe: str

class LSTMTransformerHybrid(nn.Module):
    def __init__(self, input_size: int, hidden_size: int = 128, num_layers: int = 2, 
                 num_heads: int = 8, dropout: float = 0.1):
        super(LSTMTransformerHybrid, self).__init__()
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, 
                           batch_first=True, dropout=dropout)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size,
            nhead=num_heads,
            dim_feedforward=hidden_size * 4,
            dropout=dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=2)
        
        self.attention_weights = nn.MultiheadAttention(
            embed_dim=hidden_size,
            num_heads=num_heads,
            dropout=dropout,
            batch_first=True
        )
        
        self.fc_layers = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, hidden_size // 4),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 4, 1)
        )
        
        self.confidence_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        lstm_out, (hidden, cell) = self.lstm(x)
        
        transformer_out = self.transformer(lstm_out)
        
        attended_out, attention_weights = self.attention_weights(
            transformer_out, transformer_out, transformer_out
        )
        
        final_hidden = attended_out[:, -1, :]
        
        prediction = self.fc_layers(final_hidden)
        confidence = self.confidence_head(final_hidden)
        
        return prediction, confidence, attention_weights

class TechnicalIndicators:
    @staticmethod
    def sma(prices: np.ndarray, window: int) -> np.ndarray:
        return pd.Series(prices).rolling(window=window).mean().values
    
    @staticmethod
    def ema(prices: np.ndarray, window: int) -> np.ndarray:
        return pd.Series(prices).ewm(span=window).mean().values
    
    @staticmethod
    def rsi(prices: np.ndarray, window: int = 14) -> np.ndarray:
        delta = np.diff(prices)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        avg_gain = pd.Series(gain).rolling(window=window).mean()
        avg_loss = pd.Series(loss).rolling(window=window).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return np.concatenate([[50], rsi.values])
    
    @staticmethod
    def bollinger_bands(prices: np.ndarray, window: int = 20, num_std: float = 2):
        sma = TechnicalIndicators.sma(prices, window)
        std = pd.Series(prices).rolling(window=window).std().values
        
        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)
        
        return upper_band, sma, lower_band
    
    @staticmethod
    def macd(prices: np.ndarray, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        ema_fast = TechnicalIndicators.ema(prices, fast_period)
        ema_slow = TechnicalIndicators.ema(prices, slow_period)
        
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal_period)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram

class PricePredictor:
    def __init__(self, config: Dict):
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.sequence_length = config.get('sequence_length', 60)
        self.feature_dim = config.get('feature_dim', 20)
        self.prediction_horizon = config.get('prediction_horizon', 1)
        
        self.model = LSTMTransformerHybrid(
            input_size=self.feature_dim,
            hidden_size=config.get('hidden_size', 128),
            num_layers=config.get('num_layers', 2),
            num_heads=config.get('num_heads', 8),
            dropout=config.get('dropout', 0.1)
        ).to(self.device)
        
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=config.get('learning_rate', 1e-3))
        self.criterion = nn.MSELoss()
        
        self.price_history = {}
        self.feature_scalers = {}
        self.is_trained = False
        
    def add_price_data(self, symbol: str, timestamp: float, ohlcv: Dict):
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=10000)
        
        self.price_history[symbol].append({
            'timestamp': timestamp,
            'open': ohlcv['open'],
            'high': ohlcv['high'],
            'low': ohlcv['low'],
            'close': ohlcv['close'],
            'volume': ohlcv['volume']
        })
    
    def extract_features(self, symbol: str) -> Optional[np.ndarray]:
        if symbol not in self.price_history or len(self.price_history[symbol]) < self.sequence_length + 50:
            return None
        
        data = list(self.price_history[symbol])[-200:]
        
        prices = np.array([d['close'] for d in data])
        highs = np.array([d['high'] for d in data])
        lows = np.array([d['low'] for d in data])
        volumes = np.array([d['volume'] for d in data])
        opens = np.array([d['open'] for d in data])
        
        features = []
        
        features.append(prices)
        features.append((highs - lows) / prices)
        features.append((prices - opens) / opens)
        features.append(volumes / np.mean(volumes[-50:]))
        
        features.append(TechnicalIndicators.sma(prices, 5))
        features.append(TechnicalIndicators.sma(prices, 20))
        features.append(TechnicalIndicators.ema(prices, 12))
        features.append(TechnicalIndicators.ema(prices, 26))
        
        features.append(TechnicalIndicators.rsi(prices, 14))
        
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.bollinger_bands(prices, 20)
        features.append(bb_upper)
        features.append(bb_middle)
        features.append(bb_lower)
        features.append((prices - bb_lower) / (bb_upper - bb_lower))
        
        macd_line, signal_line, histogram = TechnicalIndicators.macd(prices)
        features.append(macd_line)
        features.append(signal_line)
        features.append(histogram)
        
        log_returns = np.diff(np.log(prices))
        features.append(np.concatenate([[0], log_returns]))
        
        volatility = pd.Series(log_returns).rolling(window=20).std().values
        features.append(np.concatenate([[0], volatility]))
        
        momentum = prices / np.roll(prices, 10) - 1
        features.append(momentum)
        
        feature_matrix = np.column_stack(features)
        
        feature_matrix = feature_matrix[~np.isnan(feature_matrix).any(axis=1)]
        
        if len(feature_matrix) < self.sequence_length:
            return None
        
        return feature_matrix[-self.sequence_length:, :self.feature_dim]
    
    def predict_price(self, symbol: str) -> Optional[PredictionResult]:
        features = self.extract_features(symbol)
        
        if features is None:
            return None
        
        self.model.eval()
        
        with torch.no_grad():
            features_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)
            
            prediction, confidence, attention_weights = self.model(features_tensor)
            
            predicted_price = prediction.item()
            confidence_score = confidence.item()
            
            current_price = self.price_history[symbol][-1]['close']
            direction = "up" if predicted_price > current_price else "down"
            
            return PredictionResult(
                symbol=symbol,
                predicted_price=predicted_price,
                confidence=confidence_score,
                direction=direction,
                timeframe="1h"
            )
    
    def train_model(self, symbol: str, epochs: int = 100):
        features = self.extract_features(symbol)
        
        if features is None or len(self.price_history[symbol]) < self.sequence_length * 2:
            return False
        
        data = list(self.price_history[symbol])
        all_prices = np.array([d['close'] for d in data])
        
        X, y = [], []
        
        for i in range(self.sequence_length, len(all_prices) - self.prediction_horizon):
            feature_slice = self.extract_features_for_training(data[i-self.sequence_length:i])
            if feature_slice is not None:
                X.append(feature_slice)
                y.append(all_prices[i + self.prediction_horizon])
        
        if len(X) < 50:
            return False
        
        X = np.array(X)
        y = np.array(y)
        
        train_size = int(0.8 * len(X))
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]
        
        self.model.train()
        
        for epoch in range(epochs):
            total_loss = 0
            
            for i in range(0, len(X_train), 32):
                batch_X = torch.FloatTensor(X_train[i:i+32]).to(self.device)
                batch_y = torch.FloatTensor(y_train[i:i+32]).unsqueeze(1).to(self.device)
                
                self.optimizer.zero_grad()
                
                predictions, confidences, _ = self.model(batch_X)
                
                loss = self.criterion(predictions, batch_y)
                confidence_loss = torch.mean((1 - confidences) * torch.abs(predictions - batch_y))
                
                total_loss_batch = loss + 0.1 * confidence_loss
                total_loss_batch.backward()
                
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                
                self.optimizer.step()
                total_loss += total_loss_batch.item()
            
            if epoch % 20 == 0:
                print(f"Epoch {epoch}, Loss: {total_loss/len(X_train):.6f}")
        
        self.is_trained = True
        return True
    
    def extract_features_for_training(self, data_slice: List) -> Optional[np.ndarray]:
        if len(data_slice) < self.sequence_length:
            return None
        
        prices = np.array([d['close'] for d in data_slice])
        
        if len(prices) < 30:
            return None
        
        features = []
        features.append(prices)
        features.append(TechnicalIndicators.sma(prices, min(5, len(prices)//2)))
        features.append(TechnicalIndicators.rsi(prices, min(14, len(prices)//2)))
        
        feature_matrix = np.column_stack(features[:self.feature_dim])
        feature_matrix = feature_matrix[~np.isnan(feature_matrix).any(axis=1)]
        
        return feature_matrix[-self.sequence_length:] if len(feature_matrix) >= self.sequence_length else None
    
    def get_model_performance(self) -> Dict:
        return {
            'is_trained': self.is_trained,
            'feature_dim': self.feature_dim,
            'sequence_length': self.sequence_length,
            'prediction_horizon': self.prediction_horizon
        }
    
    def save_model(self, filepath: str):
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'config': self.config,
            'is_trained': self.is_trained
        }, filepath)
    
    def load_model(self, filepath: str):
        checkpoint = torch.load(filepath, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.is_trained = checkpoint.get('is_trained', False)
