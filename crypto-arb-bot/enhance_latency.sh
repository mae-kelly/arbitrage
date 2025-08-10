#!/bin/bash

echo "Enhancing system for sub-millisecond latency..."

cat > core/src/hft/mod.rs << 'RUST'
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};
use crossbeam::channel::{bounded, Sender, Receiver};
use parking_lot::RwLock;
use std::sync::Arc;

pub struct UltraLowLatencyEngine {
    tick_counter: AtomicU64,
    order_queue: Arc<RwLock<Vec<Order>>>,
    execution_threads: Vec<std::thread::JoinHandle<()>>,
    colocated_servers: HashMap<String, ServerConnection>,
}

#[repr(C, align(64))]
pub struct CacheLineAligned<T> {
    value: T,
    _padding: [u8; 64 - std::mem::size_of::<T>()],
}

pub struct LockFreeOrderBook {
    bids: Arc<crossbeam_skiplist::SkipMap<OrderKey, Order>>,
    asks: Arc<crossbeam_skiplist::SkipMap<OrderKey, Order>>,
    sequence: AtomicU64,
}

impl UltraLowLatencyEngine {
    pub fn new() -> Self {
        let cpu_count = num_cpus::get();
        let mut execution_threads = Vec::new();
        
        for i in 0..cpu_count {
            let handle = std::thread::spawn(move || {
                let mut cpu_set = nix::sched::CpuSet::new();
                cpu_set.set(i).unwrap();
                nix::sched::sched_setaffinity(nix::unistd::Pid::from_raw(0), &cpu_set).unwrap();
                
                loop {
                    std::hint::spin_loop();
                }
            });
            execution_threads.push(handle);
        }
        
        Self {
            tick_counter: AtomicU64::new(0),
            order_queue: Arc::new(RwLock::new(Vec::with_capacity(100000))),
            execution_threads,
            colocated_servers: HashMap::new(),
        }
    }
    
    #[inline(always)]
    pub fn process_tick(&self, data: &MarketData) -> Option<Signal> {
        let start = rdtsc();
        self.tick_counter.fetch_add(1, Ordering::Relaxed);
        
        let signal = unsafe {
            self.process_tick_unchecked(data)
        };
        
        let elapsed = rdtsc() - start;
        if elapsed > 1000 {
            tracing::warn!("Tick processing took {} cycles", elapsed);
        }
        
        signal
    }
    
    #[inline(always)]
    unsafe fn process_tick_unchecked(&self, data: &MarketData) -> Option<Signal> {
        let ptr = data as *const MarketData;
        let data_ref = &*ptr;
        
        if data_ref.spread > 0.003 {
            Some(Signal::Execute)
        } else {
            None
        }
    }
}

#[inline(always)]
fn rdtsc() -> u64 {
    unsafe {
        std::arch::x86_64::_rdtsc()
    }
}

pub struct FPGAAccelerator {
    device: opencl3::device::Device,
    program: opencl3::program::Program,
    kernel: opencl3::kernel::Kernel,
}

impl FPGAAccelerator {
    pub fn new() -> Result<Self> {
        let platform = opencl3::platform::get_platforms()?[0];
        let device = platform.get_devices(opencl3::device::CL_DEVICE_TYPE_ACCELERATOR)?[0];
        
        let kernel_source = r#"
        __kernel void arbitrage_detection(
            __global float* prices,
            __global float* spreads,
            __global int* signals,
            const int n
        ) {
            int gid = get_global_id(0);
            if (gid >= n) return;
            
            float spread = prices[gid * 2 + 1] - prices[gid * 2];
            spreads[gid] = spread;
            signals[gid] = spread > 0.003f ? 1 : 0;
        }
        "#;
        
        let context = opencl3::context::Context::from_device(&device)?;
        let program = opencl3::program::Program::create_and_build_from_source(
            &context,
            kernel_source,
            ""
        )?;
        
        let kernel = opencl3::kernel::Kernel::create(&program, "arbitrage_detection")?;
        
        Ok(Self { device, program, kernel })
    }
    
    pub fn detect_opportunities(&self, prices: &[f32]) -> Vec<bool> {
        let n = prices.len() / 2;
        let mut signals = vec![0i32; n];
        
        unsafe {
            self.kernel.set_arg(0, prices.as_ptr());
            self.kernel.set_arg(3, n as i32);
            self.kernel.enqueue_nd_range(&[n], None);
        }
        
        signals.iter().map(|&s| s == 1).collect()
    }
}

pub struct KernelBypass {
    raw_socket: i32,
    packet_buffer: Vec<u8>,
}

impl KernelBypass {
    pub fn new(interface: &str) -> Result<Self> {
        use libc::{socket, AF_PACKET, SOCK_RAW, ETH_P_ALL};
        
        let raw_socket = unsafe {
            socket(AF_PACKET, SOCK_RAW, ETH_P_ALL.to_be())
        };
        
        if raw_socket < 0 {
            return Err(anyhow::anyhow!("Failed to create raw socket"));
        }
        
        Ok(Self {
            raw_socket,
            packet_buffer: vec![0u8; 65536],
        })
    }
    
    pub fn send_order(&self, order: &Order) -> Result<()> {
        let packet = self.construct_packet(order);
        
        unsafe {
            libc::send(
                self.raw_socket,
                packet.as_ptr() as *const libc::c_void,
                packet.len(),
                0
            );
        }
        
        Ok(())
    }
    
    fn construct_packet(&self, order: &Order) -> Vec<u8> {
        let mut packet = Vec::with_capacity(1500);
        packet.extend_from_slice(&[0xFF; 6]);
        packet.extend_from_slice(&[0x00; 6]);
        packet.extend_from_slice(&(0x0800u16.to_be_bytes()));
        packet.extend_from_slice(&order.to_bytes());
        packet
    }
}
RUST

cat > core/src/hft/colocation.rs << 'RUST'
use std::net::{TcpStream, UdpSocket};
use std::io::{Read, Write};
use mio::{Poll, Events, Token, Interest};
use std::time::Duration;

pub struct ColocationManager {
    locations: HashMap<Exchange, DataCenter>,
    connections: HashMap<Exchange, DirectConnection>,
    latency_map: Arc<RwLock<HashMap<(Exchange, Exchange), Duration>>>,
}

#[derive(Clone, Hash, Eq, PartialEq)]
pub enum Exchange {
    Binance,
    Coinbase,
    FTX,
    Kraken,
    Bitstamp,
}

#[derive(Clone)]
pub struct DataCenter {
    location: String,
    ip_range: String,
    cross_connect: bool,
    latency_to_exchange: Duration,
}

pub struct DirectConnection {
    socket: TcpStream,
    fix_session: Option<FixSession>,
    sequence_number: AtomicU64,
}

impl ColocationManager {
    pub fn new() -> Self {
        let mut locations = HashMap::new();
        
        locations.insert(Exchange::Binance, DataCenter {
            location: "AWS Tokyo".to_string(),
            ip_range: "13.230.0.0/16".to_string(),
            cross_connect: true,
            latency_to_exchange: Duration::from_micros(50),
        });
        
        locations.insert(Exchange::Coinbase, DataCenter {
            location: "AWS US-East-1".to_string(),
            ip_range: "52.70.0.0/16".to_string(),
            cross_connect: true,
            latency_to_exchange: Duration::from_micros(30),
        });
        
        Self {
            locations,
            connections: HashMap::new(),
            latency_map: Arc::new(RwLock::new(HashMap::new())),
        }
    }
    
    pub async fn establish_cross_connect(&mut self, exchange: Exchange) -> Result<()> {
        let datacenter = self.locations.get(&exchange).unwrap();
        
        let socket = TcpStream::connect(&datacenter.ip_range)?;
        socket.set_nodelay(true)?;
        socket.set_nonblocking(true)?;
        
        let mut buf = [0u8; 64];
        unsafe {
            libc::setsockopt(
                socket.as_raw_fd(),
                libc::IPPROTO_TCP,
                libc::TCP_QUICKACK,
                &1 as *const _ as *const libc::c_void,
                std::mem::size_of::<i32>() as libc::socklen_t,
            );
        }
        
        let fix_session = if exchange == Exchange::Coinbase {
            Some(FixSession::new("FIX.4.4", "ARBITRAGE_BOT", "COINBASE"))
        } else {
            None
        };
        
        self.connections.insert(exchange, DirectConnection {
            socket,
            fix_session,
            sequence_number: AtomicU64::new(1),
        });
        
        Ok(())
    }
    
    pub fn send_order_microsecond(&self, exchange: Exchange, order: &Order) -> Result<Duration> {
        let start = std::time::Instant::now();
        
        let connection = self.connections.get(&exchange).unwrap();
        
        if let Some(fix) = &connection.fix_session {
            let fix_message = fix.create_new_order_single(order);
            connection.socket.write_all(fix_message.as_bytes())?;
        } else {
            let binary_order = bincode::serialize(order)?;
            connection.socket.write_all(&binary_order)?;
        }
        
        Ok(start.elapsed())
    }
}

pub struct FixSession {
    begin_string: String,
    sender_comp_id: String,
    target_comp_id: String,
}

impl FixSession {
    pub fn new(version: &str, sender: &str, target: &str) -> Self {
        Self {
            begin_string: version.to_string(),
            sender_comp_id: sender.to_string(),
            target_comp_id: target.to_string(),
        }
    }
    
    pub fn create_new_order_single(&self, order: &Order) -> String {
        format!(
            "8={}|9={}|35=D|49={}|56={}|34={}|52={}|11={}|55={}|54={}|38={}|40=2|44={}|10={}|",
            self.begin_string,
            200,
            self.sender_comp_id,
            self.target_comp_id,
            1,
            chrono::Utc::now().format("%Y%m%d-%H:%M:%S.%3f"),
            order.id,
            order.symbol,
            if order.side == Side::Buy { 1 } else { 2 },
            order.quantity,
            order.price,
            "000"
        )
    }
}
RUST

echo "HFT components added to core/src/hft/"
