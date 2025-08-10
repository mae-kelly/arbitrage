use super::*;
use chrono::{DateTime, Utc};

pub struct FundingRateArbitrage {
    threshold: f64,
    funding_rates: HashMap<String, f64>,
}

impl FundingRateArbitrage {
    pub fn new() -> Self {
        Self {
            threshold: 0.01,
            funding_rates: HashMap::new(),
        }
    }
    
    pub fn find_opportunities(&self) -> Vec<FundingOpportunity> {
        let mut opportunities = Vec::new();
        
        for (symbol, rate) in &self.funding_rates {
            if rate.abs() > self.threshold {
                opportunities.push(FundingOpportunity {
                    symbol: symbol.clone(),
                    rate: *rate,
                    action: if *rate > 0.0 { "Short" } else { "Long" }.to_string(),
                });
            }
        }
        
        opportunities
    }
}

#[derive(Debug)]
pub struct FundingOpportunity {
    pub symbol: String,
    pub rate: f64,
    pub action: String,
}
