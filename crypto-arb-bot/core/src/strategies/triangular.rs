use super::*;

pub struct TriangularArbitrage {
    min_profit_threshold: f64,
    exchanges: Vec<String>,
}

impl TriangularArbitrage {
    pub fn new() -> Self {
        Self {
            min_profit_threshold: 0.001,
            exchanges: vec!["Uniswap".to_string(), "Sushiswap".to_string()],
        }
    }
    
    pub fn find_triangular_opportunities(
        &self,
        pair_ab: f64,
        pair_bc: f64,
        pair_ca: f64,
    ) -> Option<f64> {
        let forward = pair_ab * pair_bc * pair_ca;
        
        if forward > 1.0 + self.min_profit_threshold {
            Some(forward - 1.0)
        } else {
            None
        }
    }
}
