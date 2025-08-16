#!/usr/bin/env python3
"""
Model Validation and Backtesting for Production Models
"""

import asyncio
import pandas as pd
import numpy as np
import torch
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelValidator:
    """Comprehensive model validation and backtesting"""
    
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.validation_results = {}
        
    async def load_model(self):
        """Load the trained model"""
        try:
            checkpoint = torch.load(self.model_path, map_location='cpu')
            
            # Load model architecture
            from production_training_pipeline import TransformerArbitrageModel, TrainingConfig
            config = TrainingConfig(**checkpoint['config'].__dict__)
            
            self.model = TransformerArbitrageModel(config)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.eval()
            
            self.scaler = checkpoint['scaler']
            
            logger.info("✅ Model loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            raise
    
    async def validate_on_unseen_data(self, test_data_path: str) -> Dict:
        """Validate model on completely unseen data"""
        logger.info("🧪 Starting validation on unseen data...")
        
        # Load test data
        test_data = pd.read_csv(test_data_path)
        
        # Prepare features and targets
        features, targets = self._prepare_test_data(test_data)
        
        # Run predictions
        predictions = await self._batch_predict(features)
        
        # Calculate comprehensive metrics
        metrics = self._calculate_comprehensive_metrics(predictions, targets)
        
        # Generate validation report
        report = self._generate_validation_report(metrics, predictions, targets)
        
        self.validation_results = report
        
        logger.info("✅ Validation completed")
        return report
    
    def _prepare_test_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, Dict]:
        """Prepare test data for validation"""
        # Extract features (assuming preprocessed data)
        feature_cols = [col for col in df.columns if col.startswith('feature_')]
        features = df[feature_cols].values
        
        # Scale features
        features_scaled = self.scaler.transform(features)
        
        # Create sequences
        sequence_length = 200
        sequences = []
        for i in range(len(features_scaled) - sequence_length):
            sequences.append(features_scaled[i:i+sequence_length])
        
        # Targets
        targets = {
            'price_change': df['target_price_change'].values[sequence_length:],
            'direction': df['target_direction'].values[sequence_length:],
            'actual_profit': df['actual_profit'].values[sequence_length:] if 'actual_profit' in df.columns else None
        }
        
        return np.array(sequences), targets
    
    async def _batch_predict(self, features: np.ndarray) -> Dict:
        """Run batch predictions"""
        predictions = {
            'price_change': [],
            'direction': [],
            'direction_probs': [],
            'volatility': [],
            'confidence': []
        }
        
        batch_size = 32
        
        with torch.no_grad():
            for i in range(0, len(features), batch_size):
                batch = features[i:i+batch_size]
                batch_tensor = torch.FloatTensor(batch)
                
                outputs = self.model(batch_tensor)
                
                predictions['price_change'].extend(outputs['price_change'].cpu().numpy())
                predictions['direction'].extend(torch.argmax(outputs['direction'], dim=1).cpu().numpy())
                predictions['direction_probs'].extend(torch.softmax(outputs['direction'], dim=1).cpu().numpy())
                predictions['volatility'].extend(outputs['volatility'].cpu().numpy())
                predictions['confidence'].extend(outputs['confidence'].cpu().numpy())
        
        return predictions
    
    def _calculate_comprehensive_metrics(self, predictions: Dict, targets: Dict) -> Dict:
        """Calculate comprehensive validation metrics"""
        pred_price = np.array(predictions['price_change']).flatten()
        true_price = np.array(targets['price_change'])
        
        pred_direction = np.array(predictions['direction'])
        true_direction = np.array(targets['direction'])
        
        # Basic metrics
        price_mse = np.mean((pred_price - true_price) ** 2)
        price_mae = np.mean(np.abs(pred_price - true_price))
        direction_accuracy = np.mean(pred_direction == true_direction)
        
        # Directional accuracy
        directional_accuracy = np.mean(np.sign(pred_price) == np.sign(true_price))
        
        # Trading simulation metrics
        trading_metrics = self._simulate_trading_performance(predictions, targets)
        
        # Risk metrics
        risk_metrics = self._calculate_risk_metrics(predictions, targets)
        
        # Confidence calibration
        calibration_metrics = self._calculate_confidence_calibration(predictions, targets)
        
        return {
            'basic_metrics': {
                'price_mse': float(price_mse),
                'price_mae': float(price_mae),
                'direction_accuracy': float(direction_accuracy),
                'directional_accuracy': float(directional_accuracy)
            },
            'trading_metrics': trading_metrics,
            'risk_metrics': risk_metrics,
            'calibration_metrics': calibration_metrics
        }
    
    def _simulate_trading_performance(self, predictions: Dict, targets: Dict) -> Dict:
        """Simulate trading performance"""
        pred_price = np.array(predictions['price_change']).flatten()
        true_price = np.array(targets['price_change'])
        confidence = np.array(predictions['confidence']).flatten()
        
        # Simple trading strategy: trade when confident
        confidence_threshold = 0.7
        trade_signals = confidence > confidence_threshold
        
        # Calculate returns
        predicted_returns = pred_price[trade_signals]
        actual_returns = true_price[trade_signals]
        
        # Strategy returns (only trade when predicted direction is correct)
        strategy_returns = np.where(
            np.sign(predicted_returns) == np.sign(actual_returns),
            np.abs(actual_returns),
            -np.abs(actual_returns)
        )
        
        if len(strategy_returns) > 0:
            total_return = np.sum(strategy_returns)
            win_rate = np.mean(strategy_returns > 0)
            sharpe_ratio = np.mean(strategy_returns) / (np.std(strategy_returns) + 1e-8)
            max_drawdown = self._calculate_max_drawdown(np.cumsum(strategy_returns))
        else:
            total_return = 0.0
            win_rate = 0.0
            sharpe_ratio = 0.0
            max_drawdown = 0.0
        
        return {
            'total_return': float(total_return),
            'win_rate': float(win_rate),
            'sharpe_ratio': float(sharpe_ratio),
            'max_drawdown': float(max_drawdown),
            'num_trades': int(np.sum(trade_signals)),
            'trade_frequency': float(np.mean(trade_signals))
        }
    
    def _calculate_max_drawdown(self, cumulative_returns: np.ndarray) -> float:
        """Calculate maximum drawdown"""
        if len(cumulative_returns) == 0:
            return 0.0
        
        cummax = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - cummax) / (cummax + 1e-8)
        return float(np.min(drawdown))
    
    def _calculate_risk_metrics(self, predictions: Dict, targets: Dict) -> Dict:
        """Calculate risk-related metrics"""
        pred_volatility = np.array(predictions['volatility']).flatten()
        true_price = np.array(targets['price_change'])
        
        # Calculate actual volatility (rolling std of true prices)
        window = min(50, len(true_price) // 4)
        actual_volatility = pd.Series(true_price).rolling(window).std().values[window:]
        pred_vol_aligned = pred_volatility[window:]
        
        if len(actual_volatility) > 0:
            vol_prediction_error = np.mean(np.abs(pred_vol_aligned - actual_volatility))
            vol_correlation = np.corrcoef(pred_vol_aligned, actual_volatility)[0, 1]
        else:
            vol_prediction_error = 0.0
            vol_correlation = 0.0
        
        return {
            'volatility_prediction_error': float(vol_prediction_error),
            'volatility_correlation': float(vol_correlation if not np.isnan(vol_correlation) else 0.0)
        }
    
    def _calculate_confidence_calibration(self, predictions: Dict, targets: Dict) -> Dict:
        """Calculate confidence calibration metrics"""
        confidence = np.array(predictions['confidence']).flatten()
        pred_price = np.array(predictions['price_change']).flatten()
        true_price = np.array(targets['price_change'])
        
        # Bin predictions by confidence
        n_bins = 10
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        bin_lowers = bin_boundaries[:-1]
        bin_uppers = bin_boundaries[1:]
        
        accuracies = []
        confidences = []
        
        for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
            in_bin = (confidence > bin_lower) & (confidence <= bin_upper)
            prop_in_bin = in_bin.mean()
            
            if prop_in_bin > 0:
                accuracy_in_bin = np.mean(
                    np.sign(pred_price[in_bin]) == np.sign(true_price[in_bin])
                )
                avg_confidence_in_bin = confidence[in_bin].mean()
                
                accuracies.append(accuracy_in_bin)
                confidences.append(avg_confidence_in_bin)
        
        # Expected Calibration Error
        if len(accuracies) > 0:
            ece = np.mean(np.abs(np.array(accuracies) - np.array(confidences)))
        else:
            ece = 0.0
        
        return {
            'expected_calibration_error': float(ece),
            'confidence_bins': len(accuracies)
        }
    
    def _generate_validation_report(self, metrics: Dict, predictions: Dict, targets: Dict) -> Dict:
        """Generate comprehensive validation report"""
        report = {
            'validation_timestamp': datetime.now().isoformat(),
            'model_path': self.model_path,
            'metrics': metrics,
            'summary': {
                'overall_score': self._calculate_overall_score(metrics),
                'recommendation': self._get_recommendation(metrics),
                'key_strengths': self._identify_strengths(metrics),
                'areas_for_improvement': self._identify_improvements(metrics)
            },
            'detailed_analysis': {
                'prediction_distribution': self._analyze_prediction_distribution(predictions),
                'error_analysis': self._analyze_errors(predictions, targets),
                'performance_by_regime': self._analyze_performance_by_regime(predictions, targets)
            }
        }
        
        return report
    
    def _calculate_overall_score(self, metrics: Dict) -> float:
        """Calculate overall model performance score"""
        basic = metrics['basic_metrics']
        trading = metrics['trading_metrics']
        
        # Weighted score
        directional_weight = 0.4
        trading_weight = 0.3
        risk_weight = 0.2
        calibration_weight = 0.1
        
        directional_score = basic['directional_accuracy']
        trading_score = min(trading['sharpe_ratio'] / 2.0, 1.0) if trading['sharpe_ratio'] > 0 else 0
        risk_score = 1.0 - min(abs(trading['max_drawdown']), 1.0)
        calibration_score = 1.0 - metrics['calibration_metrics']['expected_calibration_error']
        
        overall_score = (
            directional_weight * directional_score +
            trading_weight * trading_score +
            risk_weight * risk_score +
            calibration_weight * calibration_score
        )
        
        return float(overall_score)
    
    def _get_recommendation(self, metrics: Dict) -> str:
        """Get deployment recommendation"""
        overall_score = self._calculate_overall_score(metrics)
        directional_accuracy = metrics['basic_metrics']['directional_accuracy']
        sharpe_ratio = metrics['trading_metrics']['sharpe_ratio']
        
        if overall_score > 0.8 and directional_accuracy > 0.65 and sharpe_ratio > 1.0:
            return "DEPLOY - Model ready for production"
        elif overall_score > 0.6 and directional_accuracy > 0.55:
            return "CAUTION - Deploy with reduced position sizes"
        else:
            return "DO NOT DEPLOY - Model needs improvement"
    
    def _identify_strengths(self, metrics: Dict) -> List[str]:
        """Identify model strengths"""
        strengths = []
        
        if metrics['basic_metrics']['directional_accuracy'] > 0.6:
            strengths.append("Strong directional prediction accuracy")
        
        if metrics['trading_metrics']['sharpe_ratio'] > 1.0:
            strengths.append("Excellent risk-adjusted returns")
        
        if metrics['trading_metrics']['win_rate'] > 0.6:
            strengths.append("High win rate")
        
        if metrics['calibration_metrics']['expected_calibration_error'] < 0.1:
            strengths.append("Well-calibrated confidence estimates")
        
        return strengths
    
    def _identify_improvements(self, metrics: Dict) -> List[str]:
        """Identify areas for improvement"""
        improvements = []
        
        if metrics['basic_metrics']['directional_accuracy'] < 0.55:
            improvements.append("Improve directional prediction accuracy")
        
        if metrics['trading_metrics']['max_drawdown'] < -0.2:
            improvements.append("Reduce maximum drawdown")
        
        if metrics['calibration_metrics']['expected_calibration_error'] > 0.15:
            improvements.append("Better confidence calibration needed")
        
        if metrics['trading_metrics']['sharpe_ratio'] < 0.5:
            improvements.append("Improve risk-adjusted returns")
        
        return improvements
    
    def _analyze_prediction_distribution(self, predictions: Dict) -> Dict:
        """Analyze distribution of predictions"""
        pred_price = np.array(predictions['price_change']).flatten()
        confidence = np.array(predictions['confidence']).flatten()
        
        return {
            'price_change_mean': float(np.mean(pred_price)),
            'price_change_std': float(np.std(pred_price)),
            'confidence_mean': float(np.mean(confidence)),
            'confidence_std': float(np.std(confidence)),
            'direction_distribution': {
                int(k): int(v) for k, v in zip(*np.unique(predictions['direction'], return_counts=True))
            }
        }
    
    def _analyze_errors(self, predictions: Dict, targets: Dict) -> Dict:
        """Analyze prediction errors"""
        pred_price = np.array(predictions['price_change']).flatten()
        true_price = np.array(targets['price_change'])
        errors = pred_price - true_price
        
        return {
            'mean_error': float(np.mean(errors)),
            'error_std': float(np.std(errors)),
            'median_error': float(np.median(errors)),
            'error_skewness': float(self._calculate_skewness(errors)),
            'large_error_rate': float(np.mean(np.abs(errors) > 2 * np.std(errors)))
        }
    
    def _calculate_skewness(self, data: np.ndarray) -> float:
        """Calculate skewness of data"""
        if len(data) == 0:
            return 0.0
        
        mean = np.mean(data)
        std = np.std(data)
        
        if std == 0:
            return 0.0
        
        return np.mean(((data - mean) / std) ** 3)
    
    def _analyze_performance_by_regime(self, predictions: Dict, targets: Dict) -> Dict:
        """Analyze performance by market regime"""
        pred_price = np.array(predictions['price_change']).flatten()
        true_price = np.array(targets['price_change'])
        
        # Define regimes based on volatility
        volatility = pd.Series(true_price).rolling(20).std()
        vol_quantiles = volatility.quantile([0.33, 0.67])
        
        low_vol = volatility <= vol_quantiles.iloc[0]
        high_vol = volatility >= vol_quantiles.iloc[1]
        med_vol = ~(low_vol | high_vol)
        
        regimes = {
            'low_volatility': low_vol,
            'medium_volatility': med_vol,
            'high_volatility': high_vol
        }
        
        regime_performance = {}
        
        for regime_name, regime_mask in regimes.items():
            if np.sum(regime_mask) > 0:
                regime_pred = pred_price[regime_mask]
                regime_true = true_price[regime_mask]
                
                directional_acc = np.mean(np.sign(regime_pred) == np.sign(regime_true))
                mse = np.mean((regime_pred - regime_true) ** 2)
                
                regime_performance[regime_name] = {
                    'directional_accuracy': float(directional_acc),
                    'mse': float(mse),
                    'sample_count': int(np.sum(regime_mask))
                }
        
        return regime_performance
    
    async def save_validation_report(self, output_path: str):
        """Save validation report to file"""
        with open(output_path, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        
        logger.info(f"✅ Validation report saved to {output_path}")

async def main():
    """Main validation function"""
    validator = ModelValidator('models/production/arbitrage_transformer_v1.pth')
    
    try:
        await validator.load_model()
        
        # Run validation (assuming test data exists)
        test_data_path = 'data/test_data.csv'
        results = await validator.validate_on_unseen_data(test_data_path)
        
        # Save report
        await validator.save_validation_report('models/validation_report.json')
        
        print("🎉 Validation completed successfully!")
        print(f"📊 Overall Score: {results['summary']['overall_score']:.3f}")
        print(f"🎯 Recommendation: {results['summary']['recommendation']}")
        
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
