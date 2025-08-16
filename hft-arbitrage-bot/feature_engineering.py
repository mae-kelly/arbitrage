#!/usr/bin/env python3
"""
Advanced feature engineering for ML models
"""

import pandas as pd
import numpy as np
import talib
from sklearn.preprocessing import StandardScaler, RobustScaler
import sqlite3

class FeatureEngineer:
    def __init__(self):
        self.scaler = StandardScaler()
        
    def create_price_features(self, df):
        """Create price-based features"""
        features = pd.DataFrame(index=df.index)
        
        # Basic price features
        features['returns'] = df['close'].pct_change()
        features['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        features['volatility'] = features['returns'].rolling(20).std()
        
        # Technical indicators
        features['rsi'] = talib.RSI(df['close'].values)
        features['macd'], features['macd_signal'], features['macd_hist'] = talib.MACD(df['close'].values)
        features['bb_upper'], features['bb_middle'], features['bb_lower'] = talib.BBANDS(df['close'].values)
        
        # Volume features
        features['volume_sma'] = df['volume'].rolling(20).mean()
        features['volume_ratio'] = df['volume'] / features['volume_sma']
        
        # Microstructure features
        if 'bid_price' in df.columns:
            features['spread'] = df['ask_price'] - df['bid_price']
            features['mid_price'] = (df['ask_price'] + df['bid_price']) / 2
            features['spread_bps'] = features['spread'] / features['mid_price'] * 10000
        
        return features.fillna(method='ffill').fillna(0)
    
    def create_arbitrage_features(self, multi_exchange_data):
        """Create arbitrage-specific features"""
        features = []
        
        for timestamp, group in multi_exchange_data.groupby('timestamp'):
            if len(group) >= 2:  # Need at least 2 exchanges
                exchanges = group.set_index('exchange')
                
                # Calculate all pairwise price differences
                for ex1 in exchanges.index:
                    for ex2 in exchanges.index:
                        if ex1 != ex2:
                            price_diff = exchanges.loc[ex2, 'bid_price'] - exchanges.loc[ex1, 'ask_price']
                            profit_pct = price_diff / exchanges.loc[ex1, 'ask_price'] * 100
                            
                            features.append({
                                'timestamp': timestamp,
                                'buy_exchange': ex1,
                                'sell_exchange': ex2,
                                'price_difference': price_diff,
                                'profit_percentage': profit_pct,
                                'buy_liquidity': exchanges.loc[ex1, 'ask_liquidity'],
                                'sell_liquidity': exchanges.loc[ex2, 'bid_liquidity'],
                                'combined_spread': exchanges.loc[ex1, 'spread'] + exchanges.loc[ex2, 'spread'],
                            })
        
        return pd.DataFrame(features)

def main():
    print("🔧 Starting feature engineering...")
    
    # Load raw data
    with sqlite3.connect('training_data/market_data.db') as conn:
        orderbook_data = pd.read_sql('SELECT * FROM orderbooks', conn)
    
    engineer = FeatureEngineer()
    
    # Create arbitrage features
    arb_features = engineer.create_arbitrage_features(orderbook_data)
    
    # Save processed features
    with sqlite3.connect('training_data/features.db') as conn:
        arb_features.to_sql('arbitrage_features', conn, if_exists='replace', index=False)
    
    print(f"✅ Created {len(arb_features)} arbitrage feature records")

if __name__ == "__main__":
    main()
