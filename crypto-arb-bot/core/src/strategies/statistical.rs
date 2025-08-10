use super::*;
use std::collections::VecDeque;

pub struct StatisticalArbitrage {
    lookback_period: usize,
    z_score_threshold: f64,
    price_history: HashMap<String, VecDeque<f64>>,
}

impl StatisticalArbitrage {
    pub fn new() -> Self {
        Self {
            lookback_period: 1000,
            z_score_threshold: 2.0,
            price_history: HashMap::new(),
        }
    }
    
    pub fn calculate_z_score(&self, asset: &str) -> Option<f64> {
        let prices = self.price_history.get(asset)?;
        if prices.len() < 2 {
            return None;
        }
        
        let mean: f64 = prices.iter().sum::<f64>() / prices.len() as f64;
        let variance: f64 = prices.iter().map(|p| (p - mean).powi(2)).sum::<f64>() / prices.len() as f64;
        let std_dev = variance.sqrt();
        
        if std_dev == 0.0 {
            return None;
        }
        
        Some((prices.back()? - mean) / std_dev)
    }
    
    pub fn find_pairs(&self, assets: &[String]) -> Vec<(String, String, f64)> {
        let mut pairs = Vec::new();
        
        for i in 0..assets.len() {
            for j in i+1..assets.len() {
                if let (Some(z1), Some(z2)) = (
                    self.calculate_z_score(&assets[i]),
                    self.calculate_z_score(&assets[j])
                ) {
                    let correlation = (z1 - z2).abs();
                    if correlation > self.z_score_threshold {
                        pairs.push((assets[i].clone(), assets[j].clone(), correlation));
                    }
                }
            }
        }
        
        pairs
    }
}
