use std::sync::atomic::{AtomicU32, AtomicU64, Ordering};
use std::sync::Arc;
use crossbeam::channel::{bounded, Receiver, Sender};

#[repr(C, packed)]
#[derive(Clone, Copy)]
pub struct UltraPrice {
    pub bid: f32,
    pub ask: f32,
    pub exchange_id: u8,
    pub timestamp: u32,
}

#[repr(C, packed)]
#[derive(Clone, Copy)]
pub struct UltraOpportunity {
    pub coin_id: u16,
    pub buy_ex: u8,
    pub sell_ex: u8,
    pub profit_bps: u16,
    pub amount: f32,
}

pub struct UltraEngine {
    // Lock-free price grid: [coin_id][exchange_id]
    prices: Vec<Vec<AtomicU64>>,
    opportunity_tx: Sender<UltraOpportunity>,
    opportunity_rx: Receiver<UltraOpportunity>,
    scan_counter: AtomicU64,
    opportunity_counter: AtomicU64,
}

impl UltraEngine {
    pub fn new(max_coins: usize, max_exchanges: usize) -> Self {
        let (tx, rx) = bounded(100_000);
        let mut prices = Vec::with_capacity(max_coins);
        
        for _ in 0..max_coins {
            let mut exchange_prices = Vec::with_capacity(max_exchanges);
            for _ in 0..max_exchanges {
                exchange_prices.push(AtomicU64::new(0));
            }
            prices.push(exchange_prices);
        }

        Self {
            prices,
            opportunity_tx: tx,
            opportunity_rx: rx,
            scan_counter: AtomicU64::new(0),
            opportunity_counter: AtomicU64::new(0),
        }
    }

    #[inline(always)]
    pub fn update_price(&self, coin_id: u16, exchange_id: u8, price: UltraPrice) {
        if (coin_id as usize) < self.prices.len() && 
           (exchange_id as usize) < self.prices[coin_id as usize].len() {
            
            let packed = unsafe { std::mem::transmute::<UltraPrice, u64>(price) };
            self.prices[coin_id as usize][exchange_id as usize]
                .store(packed, Ordering::Relaxed);
        }
    }

    pub fn ultra_scan(&self) -> u64 {
        let start = std::time::Instant::now();
        let mut found = 0u64;

        // Scan top 100 coins across top 20 exchanges for speed
        for coin_id in 0..100u16 {
            for buy_ex in 0..20u8 {
                for sell_ex in 0..20u8 {
                    if buy_ex == sell_ex { continue; }

                    let buy_packed = self.prices[coin_id as usize][buy_ex as usize]
                        .load(Ordering::Relaxed);
                    let sell_packed = self.prices[coin_id as usize][sell_ex as usize]
                        .load(Ordering::Relaxed);

                    if buy_packed != 0 && sell_packed != 0 {
                        let buy_price: UltraPrice = unsafe { 
                            std::mem::transmute(buy_packed) 
                        };
                        let sell_price: UltraPrice = unsafe { 
                            std::mem::transmute(sell_packed) 
                        };

                        if sell_price.bid > buy_price.ask && buy_price.ask > 0.0 {
                            let profit_bps = (((sell_price.bid - buy_price.ask) / buy_price.ask) * 1_000_000.0) as u16;
                            
                            if profit_bps > 500 { // >0.05%
                                found += 1;
                                let _ = self.opportunity_tx.try_send(UltraOpportunity {
                                    coin_id,
                                    buy_ex,
                                    sell_ex,
                                    profit_bps,
                                    amount: 10000.0,
                                });
                            }
                        }
                    }
                }
            }
        }

        self.scan_counter.fetch_add(1, Ordering::Relaxed);
        self.opportunity_counter.fetch_add(found, Ordering::Relaxed);

        let elapsed = start.elapsed();
        if elapsed.as_micros() < 100 {
            println!("🎯 TARGET HIT: {}μs scan time!", elapsed.as_micros());
        }

        found
    }

    pub fn get_opportunities(&self) -> Vec<UltraOpportunity> {
        let mut opps = Vec::new();
        while let Ok(opp) = self.opportunity_rx.try_recv() {
            opps.push(opp);
        }
        opps
    }
}
