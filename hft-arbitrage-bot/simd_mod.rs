//! SIMD-optimized price scanning and arbitrage detection

use std::arch::x86_64::*;
use anyhow::Result;

#[derive(Debug, Clone)]
pub struct SIMDPriceScanner {
    prices_buffer: Vec<f32>,
    opportunities_buffer: Vec<f32>,
    batch_size: usize,
}

impl SIMDPriceScanner {
    pub fn new(max_pairs: usize) -> Self {
        let batch_size = (max_pairs / 8) * 8; // Align to 8 for AVX
        
        Self {
            prices_buffer: vec![0.0; batch_size],
            opportunities_buffer: vec![0.0; batch_size],
            batch_size,
        }
    }
    
    #[target_feature(enable = "avx2")]
    pub unsafe fn scan_arbitrage_opportunities_avx2(
        &mut self,
        buy_prices: &[f32],
        sell_prices: &[f32],
        min_profit_threshold: f32,
    ) -> u32 {
        assert_eq!(buy_prices.len(), sell_prices.len());
        assert!(buy_prices.len() <= self.batch_size);
        
        let threshold_vec = _mm256_set1_ps(min_profit_threshold);
        let mut opportunities_found = 0u32;
        
        for chunk_start in (0..buy_prices.len()).step_by(8) {
            if chunk_start + 8 > buy_prices.len() {
                break;
            }
            
            // Load 8 buy prices and 8 sell prices
            let buy_vec = _mm256_loadu_ps(buy_prices.as_ptr().add(chunk_start));
            let sell_vec = _mm256_loadu_ps(sell_prices.as_ptr().add(chunk_start));
            
            // Calculate profit percentage: (sell - buy) / buy
            let diff_vec = _mm256_sub_ps(sell_vec, buy_vec);
            let profit_pct_vec = _mm256_div_ps(diff_vec, buy_vec);
            
            // Compare with threshold
            let mask = _mm256_cmp_ps(profit_pct_vec, threshold_vec, _CMP_GT_OQ);
            
            // Count profitable opportunities
            let mask_bits = _mm256_movemask_ps(mask);
            opportunities_found += mask_bits.count_ones();
            
            // Store profitable opportunities
            _mm256_storeu_ps(
                self.opportunities_buffer.as_mut_ptr().add(chunk_start),
                profit_pct_vec
            );
        }
        
        opportunities_found
    }
    
    #[target_feature(enable = "avx512f")]
    pub unsafe fn scan_arbitrage_opportunities_avx512(
        &mut self,
        buy_prices: &[f32],
        sell_prices: &[f32], 
        min_profit_threshold: f32,
    ) -> u32 {
        let threshold_vec = _mm512_set1_ps(min_profit_threshold);
        let mut opportunities_found = 0u32;
        
        for chunk_start in (0..buy_prices.len()).step_by(16) {
            if chunk_start + 16 > buy_prices.len() {
                break;
            }
            
            // Load 16 prices at once with AVX-512
            let buy_vec = _mm512_loadu_ps(buy_prices.as_ptr().add(chunk_start));
            let sell_vec = _mm512_loadu_ps(sell_prices.as_ptr().add(chunk_start));
            
            // Calculate profit percentage
            let diff_vec = _mm512_sub_ps(sell_vec, buy_vec);
            let profit_pct_vec = _mm512_div_ps(diff_vec, buy_vec);
            
            // Compare with threshold using mask
            let profitable_mask = _mm512_cmp_ps_mask(
                profit_pct_vec, 
                threshold_vec, 
                _CMP_GT_OQ
            );
            
            // Count opportunities
            opportunities_found += profitable_mask.count_ones();
            
            // Store results using mask
            _mm512_mask_storeu_ps(
                self.opportunities_buffer.as_mut_ptr().add(chunk_start),
                profitable_mask,
                profit_pct_vec
            );
        }
        
        opportunities_found
    }
    
    pub fn scan_opportunities(&mut self, buy_prices: &[f32], sell_prices: &[f32], threshold: f32) -> u32 {
        if is_x86_feature_detected!("avx512f") {
            unsafe { self.scan_arbitrage_opportunities_avx512(buy_prices, sell_prices, threshold) }
        } else if is_x86_feature_detected!("avx2") {
            unsafe { self.scan_arbitrage_opportunities_avx2(buy_prices, sell_prices, threshold) }
        } else {
            // Fallback to scalar implementation
            self.scan_opportunities_scalar(buy_prices, sell_prices, threshold)
        }
    }
    
    fn scan_opportunities_scalar(&mut self, buy_prices: &[f32], sell_prices: &[f32], threshold: f32) -> u32 {
        let mut count = 0;
        for i in 0..buy_prices.len().min(sell_prices.len()) {
            let profit_pct = (sell_prices[i] - buy_prices[i]) / buy_prices[i];
            if profit_pct > threshold {
                count += 1;
                if i < self.opportunities_buffer.len() {
                    self.opportunities_buffer[i] = profit_pct;
                }
            }
        }
        count
    }
    
    pub fn get_opportunities(&self, count: usize) -> &[f32] {
        &self.opportunities_buffer[..count.min(self.opportunities_buffer.len())]
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_simd_scanner_performance() {
        let mut scanner = SIMDPriceScanner::new(10000);
        let buy_prices: Vec<f32> = (0..10000).map(|i| 100.0 + i as f32 * 0.01).collect();
        let sell_prices: Vec<f32> = (0..10000).map(|i| 100.5 + i as f32 * 0.01).collect();
        
        let start = std::time::Instant::now();
        let opportunities = scanner.scan_opportunities(&buy_prices, &sell_prices, 0.001);
        let duration = start.elapsed();
        
        println!("SIMD scan found {} opportunities in {}μs", opportunities, duration.as_micros());
        assert!(duration.as_micros() < 1000); // Should complete in under 1ms
    }
}
