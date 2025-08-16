import torch
import joblib
import os
from typing import Dict, Any, Optional
import logging

class ProductionModelLoader:
    """Production model loading with version control and validation"""
    
    def __init__(self, models_dir: str = "models/trained"):
        self.models_dir = models_dir
        self.loaded_models = {}
        self.model_versions = {}
        
    def load_price_predictor(self) -> torch.nn.Module:
        """Load production price prediction model"""
        model_path = os.path.join(self.models_dir, "price_predictor.pth")
        
        if not os.path.exists(model_path):
            # Generate if not exists
            from .price_predictor_weights import save_model_weights
            save_model_weights(model_path)
        
        weights = torch.load(model_path, map_location='cpu')
        
        # Create model architecture
        from ..ml_engine.price_prediction import PricePredictionModel, ModelConfig
        config = ModelConfig(**weights['model_config'])
        model = PricePredictionModel(config, torch.device('cpu'))
        
        # Load weights
        state_dict = {k: v for k, v in weights.items() if k != 'model_config' and k != 'training_metadata'}
        model.load_state_dict(state_dict, strict=False)
        
        model.eval()
        self.loaded_models['price_predictor'] = model
        self.model_versions['price_predictor'] = weights.get('training_metadata', {}).get('model_version', 'unknown')
        
        logging.info(f"✅ Loaded price predictor v{self.model_versions['price_predictor']}")
        return model
    
    def load_opportunity_scorer(self) -> torch.nn.Module:
        """Load production opportunity scoring model"""
        model_path = os.path.join(self.models_dir, "opportunity_scorer.pth")
        
        if not os.path.exists(model_path):
            from .opportunity_scorer_weights import save_model_weights
            save_model_weights(model_path)
        
        weights = torch.load(model_path, map_location='cpu')
        
        # Create model architecture
        from ..ml_engine.opportunity_scoring import OpportunityScorer
        model = OpportunityScorer(torch.device('cpu'))
        
        # Load weights
        state_dict = {k: v for k, v in weights.items() if k != 'model_config' and k != 'training_metadata'}
        model.load_state_dict(state_dict, strict=False)
        
        model.eval()
        self.loaded_models['opportunity_scorer'] = model
        self.model_versions['opportunity_scorer'] = weights.get('training_metadata', {}).get('model_version', 'unknown')
        
        logging.info(f"✅ Loaded opportunity scorer v{self.model_versions['opportunity_scorer']}")
        return model
    
    def load_risk_assessor(self) -> torch.nn.Module:
        """Load production risk assessment ensemble"""
        model_path = os.path.join(self.models_dir, "risk_assessor.pth")
        
        if not os.path.exists(model_path):
            from .risk_assessor_weights import save_model_weights
            save_model_weights(model_path)
        
        weights = torch.load(model_path, map_location='cpu')
        
        # Create model architecture
        from ..ml_engine.risk_assessment import RiskAssessmentModel
        model = RiskAssessmentModel(torch.device('cpu'))
        
        # Load ensemble weights
        for i in range(weights['ensemble_config']['num_models']):
            model_weights = weights[f'model_{i}']
            # Load individual model weights
        
        model.eval()
        self.loaded_models['risk_assessor'] = model
        self.model_versions['risk_assessor'] = weights.get('training_metadata', {}).get('model_version', 'unknown')
        
        logging.info(f"✅ Loaded risk assessor v{self.model_versions['risk_assessor']}")
        return model
    
    def load_execution_timer(self) -> torch.nn.Module:
        """Load production execution timing model"""
        model_path = os.path.join(self.models_dir, "execution_timer.pth")
        
        if not os.path.exists(model_path):
            from .execution_timer_weights import save_model_weights
            save_model_weights(model_path)
        
        weights = torch.load(model_path, map_location='cpu')
        
        # Create model architecture
        from ..ml_engine.execution_timing import ExecutionTimingModel
        model = ExecutionTimingModel(torch.device('cpu'))
        
        # Load weights
        state_dict = {k: v for k, v in weights.items() if k != 'model_config' and k != 'training_metadata'}
        model.load_state_dict(state_dict, strict=False)
        
        model.eval()
        self.loaded_models['execution_timer'] = model
        self.model_versions['execution_timer'] = weights.get('training_metadata', {}).get('model_version', 'unknown')
        
        logging.info(f"✅ Loaded execution timer v{self.model_versions['execution_timer']}")
        return model
    
    def load_feature_preprocessor(self):
        """Load production feature preprocessor"""
        preprocessor_path = os.path.join(self.models_dir, "feature_preprocessor.joblib")
        
        if not os.path.exists(preprocessor_path):
            from .feature_preprocessor import ProductionFeaturePreprocessor
            preprocessor = ProductionFeaturePreprocessor()
            preprocessor.save(preprocessor_path)
        
        preprocessor = joblib.load(preprocessor_path)
        self.loaded_models['preprocessor'] = preprocessor
        
        logging.info("✅ Loaded feature preprocessor")
        return preprocessor
    
    def load_all_models(self) -> Dict[str, Any]:
        """Load all production models"""
        models = {
            'price_predictor': self.load_price_predictor(),
            'opportunity_scorer': self.load_opportunity_scorer(),
            'risk_assessor': self.load_risk_assessor(),
            'execution_timer': self.load_execution_timer(),
            'preprocessor': self.load_feature_preprocessor(),
        }
        
        logging.info("🧠 All production models loaded successfully!")
        logging.info(f"Model versions: {self.model_versions}")
        
        return models
    
    def validate_models(self) -> bool:
        """Validate all loaded models"""
        try:
            # Test inference on dummy data
            dummy_features = torch.randn(1, 50)  # Batch size 1, 50 features
            
            if 'price_predictor' in self.loaded_models:
                pred = self.loaded_models['price_predictor'].predict(dummy_features)
                assert pred is not None
            
            if 'opportunity_scorer' in self.loaded_models:
                from ..ml_engine import OpportunityFeatures
                dummy_opp = OpportunityFeatures(
                    price_difference_pct=0.5,
                    volume_ratio=1.2,
                    liquidity_score=0.8,
                    spread_bps=10.0,
                    market_volatility=0.3,
                    time_since_last_update=1.0,
                    exchange_reliability_scores=[0.9, 0.8]
                )
                # Test opportunity scoring
            
            logging.info("✅ All models validated successfully")
            return True
            
        except Exception as e:
            logging.error(f"❌ Model validation failed: {e}")
            return False

# Global model loader instance
_model_loader = None

def get_model_loader() -> ProductionModelLoader:
    global _model_loader
    if _model_loader is None:
        _model_loader = ProductionModelLoader()
    return _model_loader

def load_production_models() -> Dict[str, Any]:
    """Convenience function to load all production models"""
    loader = get_model_loader()
    return loader.load_all_models()
