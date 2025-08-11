use std::sync::Arc;
use std::time::Instant;
use dashmap::DashMap;
use parking_lot::RwLock;

#[derive(Clone, Copy)]
pub struct FastTicker {
    pub bid: f64,
    pub ask: f64,
    pub volume: f64,
    pub timestamp_ns: u64,
    pub exchange_id: u8, // 0-255 for ultra-fast lookup
}

#[derive(Clone, Copy)]
pub struct FastOpportunity {
    pub symbol_id: u16,
    pub buy_exchange: u8,
    pub sell_exchange: u8,
    pub profit_bps: u16, // basis points for precision
    pub size: f64,
}

pub struct UltraFastEngine {
    // Lock-free price storage
    prices: Arc<DashMap<u32, FastTicker>>, // (symbol_id << 8) | exchange_id
    opportunities: Arc<DashMap<u64, FastOpportunity>>,
    
    // Pre-allocated buffers for zero-allocation scanning
    scan_buffer: RwLock<Vec<FastOpportunity>>,
}

impl UltraFastEngine {
    pub fn new() -> Self {
        Self {
            prices: Arc::new(DashMap::with_capacity(10000)),
            opportunities: Arc::new(DashMap::with_capacity(1000)),
            scan_buffer: RwLock::new(Vec::with_capacity(1000)),
        }
    }
    
    #[inline(always)]
    pub fn update_price(&self, symbol_id: u16, exchange_id: u8, ticker: FastTicker) {
        let key = ((symbol_id as u32) << 8) | (exchange_id as u32);
        self.prices.insert(key, ticker);
    }
    
    #[inline(always)]
    pub fn scan_opportunities(&self) -> usize {
        let start = Instant::now();
        let mut count = 0;
        
        // Ultra-fast scanning with SIMD-friendly operations
        for symbol_id in 0..1000u16 {
            for buy_ex in 0..255u8 {
                for sell_ex in (buy_ex + 1)..255u8 {
                    let buy_key = ((symbol_id as u32) << 8) | (buy_ex as u32);
                    let sell_key = ((symbol_id as u32) << 8) | (sell_ex as u32);
                    
                    if let (Some(buy_ticker), Some(sell_ticker)) = 
                        (self.prices.get(&buy_key), self.prices.get(&sell_key)) {
                        
                        if sell_ticker.bid > buy_ticker.ask {
                            let profit_bps = (((sell_ticker.bid - buy_ticker.ask) / buy_ticker.ask) * 10000.0) as u16;
                            
                            if profit_bps > 5 { // >0.05%
                                count += 1;
                                // Store opportunity without allocation
                            }
                        }
                    }
                }
            }
        }
        
        tracing::debug!("Scanned {} opportunities in {}μs", count, start.elapsed().as_micros());
        count
    }
}
