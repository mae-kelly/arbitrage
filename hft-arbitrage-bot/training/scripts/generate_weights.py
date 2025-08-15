#!/usr/bin/env python3
"""Generate all production model weights"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from models.trained.price_predictor_weights import save_model_weights as save_price
from models.trained.opportunity_scorer_weights import save_model_weights as save_opportunity
from models.trained.risk_assessor_weights import save_model_weights as save_risk
from models.trained.execution_timer_weights import save_model_weights as save_timing
from models.trained.feature_preprocessor import ProductionFeaturePreprocessor

def generate_all_weights():
    """Generate all production model weights"""
    print("🧠 Generating production model weights...")
    
    os.makedirs("models/trained", exist_ok=True)
    
    # Generate model weights
    save_price("models/trained/price_predictor.pth")
    save_opportunity("models/trained/opportunity_scorer.pth")
    save_risk("models/trained/risk_assessor.pth")
    save_timing("models/trained/execution_timer.pth")
    
    # Generate preprocessor
    preprocessor = ProductionFeaturePreprocessor()
    preprocessor.save("models/trained/feature_preprocessor.joblib")
    
    print("✅ All production model weights generated!")
    print(f"📁 Models saved to: {os.path.abspath('models/trained')}")

if __name__ == "__main__":
    generate_all_weights()
