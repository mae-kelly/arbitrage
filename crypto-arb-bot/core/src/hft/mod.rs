pub mod colocation;
pub mod fpga;
pub mod kernel_bypass;

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};
use crossbeam::channel::{bounded, Sender, Receiver};
use parking_lot::RwLock;
use std::sync::Arc;
use std::collections::HashMap;
use anyhow::Result;

pub struct UltraLowLatencyEngine {
    tick_counter: AtomicU64,
    order_queue: Arc<RwLock<Vec<Order>>>,
    colocated_servers: HashMap<String, ServerConnection>,
}

#[repr(C, align(64))]
pub struct CacheLineAligned<T> {
    value: T,
}

#[derive(Clone, Debug)]
pub struct Order {
    pub id: String,
    pub symbol: String,
    pub side: Side,
    pub quantity: f64,
    pub price: f64,
}

#[derive(Clone, Debug)]
pub enum Side {
    Buy,
    Sell,
}

pub struct ServerConnection {
    endpoint: String,
    latency_ns: u64,
}

impl UltraLowLatencyEngine {
    pub fn new() -> Result<Self> {
        Ok(Self {
            tick_counter: AtomicU64::new(0),
            order_queue: Arc::new(RwLock::new(Vec::with_capacity(100000))),
            colocated_servers: HashMap::new(),
        })
    }
    
    #[inline(always)]
    pub fn process_tick(&self, data: &MarketData) -> Option<Signal> {
        let start = rdtsc();
        self.tick_counter.fetch_add(1, Ordering::Relaxed);
        
        let signal = if data.spread > 0.003 {
            Some(Signal::Execute)
        } else {
            None
        };
        
        let elapsed = rdtsc() - start;
        if elapsed > 1000 {
            tracing::warn!("Tick processing took {} cycles", elapsed);
        }
        
        signal
    }
}

#[inline(always)]
fn rdtsc() -> u64 {
    #[cfg(target_arch = "x86_64")]
    unsafe {
        std::arch::x86_64::_rdtsc()
    }
    #[cfg(not(target_arch = "x86_64"))]
    {
        std::time::Instant::now().elapsed().as_nanos() as u64
    }
}

#[derive(Debug)]
pub struct MarketData {
    pub spread: f64,
}

#[derive(Debug)]
pub enum Signal {
    Execute,
    Wait,
}
