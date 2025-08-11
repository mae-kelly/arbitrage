use metal::*;
use std::time::Instant;
use std::mem;
use std::ptr;
use anyhow::{Result, anyhow};
use tracing::{info, debug};

// Ultra-optimized price structure matching Metal shader
#[repr(C)]
#[derive(Clone, Copy)]
pub struct UltraPrice {
    pub bid_ask: [f32; 2],      // [bid, ask]
    pub vol_time: [f32; 2],     // [volume, timestamp]
    pub exchange_coin: u32,     // exchange_id << 16 | coin_id
}

pub struct UltraOptimizedGPUEngine {
    device: Device,
    command_queue: CommandQueue,
    compute_pipeline: ComputePipelineState,
    init_pipeline: ComputePipelineState,
    
    // Pre-allocated GPU buffers for zero-allocation scanning
    price_buffer: Buffer,
    opportunity_count_buffer: Buffer,
    opportunities_buffer: Buffer,
    
    // Performance optimizations
    max_prices: usize,
    threadgroup_size: MTLSize,
    thread_groups: MTLSize,
}

impl UltraOptimizedGPUEngine {
    pub fn new() -> Result<Self> {
        let device = Device::system_default()
            .ok_or_else(|| anyhow!("M1 GPU required for <10μs performance"))?;
        
        if !device.name().contains("Apple") {
            return Err(anyhow!("Apple Silicon GPU required"));
        }
        
        info!("🔥 Initializing ULTRA-OPTIMIZED M1 GPU: {}", device.name());
        
        // Disable Metal validation for maximum performance
        std::env::set_var("MTL_SHADER_VALIDATION", "0");
        std::env::set_var("MTL_API_VALIDATION", "0");
        
        let command_queue = device.new_command_queue();
        
        // Compile ultra-optimized Metal shaders
        let shader_source = include_str!("../metal_kernels/ultra_fast_arbitrage.metal");
        let library = device.new_library_with_source(shader_source, &CompileOptions::new())
            .map_err(|e| anyhow!("Failed to compile ultra-fast shaders: {:?}", e))?;
        
        let compute_function = library.get_function("ultra_fast_arbitrage_scan", None)
            .map_err(|e| anyhow!("Failed to load compute function: {:?}", e))?;
        let compute_pipeline = device.new_compute_pipeline_state_with_function(&compute_function)
            .map_err(|e| anyhow!("Failed to create compute pipeline: {:?}", e))?;
        
        let init_function = library.get_function("initialize_buffers", None)
            .map_err(|e| anyhow!("Failed to load init function: {:?}", e))?;
        let init_pipeline = device.new_compute_pipeline_state_with_function(&init_function)
            .map_err(|e| anyhow!("Failed to create init pipeline: {:?}", e))?;
        
        // Pre-allocate GPU buffers for maximum performance
        let max_prices = 1000usize;
        let price_buffer_size = max_prices * mem::size_of::<UltraPrice>();
        let price_buffer = device.new_buffer(price_buffer_size as u64, 
            MTLResourceOptions::StorageModeShared | MTLResourceOptions::CPUCacheModeWriteCombined);
        
        let opportunity_count_buffer = device.new_buffer(mem::size_of::<u32>() as u64,
            MTLResourceOptions::StorageModeShared);
        
        let opportunities_buffer = device.new_buffer((10000 * mem::size_of::<[u32; 2]>()) as u64,
            MTLResourceOptions::StorageModeShared);
        
        // Optimize threadgroup configuration for M1 GPU
        let threadgroup_size = MTLSize::new(32, 32, 1);  // 1024 threads per group (optimal for M1)
        let thread_groups = MTLSize::new(
            (max_prices + 31) / 32,
            (max_prices + 31) / 32,
            1
        );
        
        info!("✅ Ultra-optimized M1 GPU engine ready");
        info!("🎯 Target: <10μs arbitrage scanning");
        info!("⚡ Buffers pre-allocated, validation disabled");
        
        Ok(Self {
            device,
            command_queue,
            compute_pipeline,
            init_pipeline,
            price_buffer,
            opportunity_count_buffer,
            opportunities_buffer,
            max_prices,
            threadgroup_size,
            thread_groups,
        })
    }
    
    pub fn ultra_fast_scan(&self, prices: &[(String, String, f64, f64)]) -> Result<(u64, u64)> {
        let scan_start = Instant::now();
        
        if prices.is_empty() {
            return Ok((0, 0));
        }
        
        let num_prices = prices.len().min(self.max_prices);
        
        // Convert to ultra-optimized format with SIMD-friendly layout
        let ultra_prices: Vec<UltraPrice> = prices.iter().take(num_prices).enumerate().map(|(i, (exchange, coin, bid, ask))| {
            let exchange_id = self.exchange_to_id(exchange) as u32;
            let coin_id = self.coin_to_id(coin) as u32;
            let exchange_coin = (exchange_id << 16) | coin_id;
            
            UltraPrice {
                bid_ask: [*bid as f32, *ask as f32],
                vol_time: [1000.0, i as f32],
                exchange_coin,
            }
        }).collect();
        
        // Ultra-fast GPU memory update
        unsafe {
            let ptr = self.price_buffer.contents() as *mut UltraPrice;
            ptr::copy_nonoverlapping(ultra_prices.as_ptr(), ptr, num_prices);
        }
        
        // Create asynchronous command buffer for maximum performance
        let command_buffer = self.command_queue.new_command_buffer();
        command_buffer.set_label("UltraFastArbitrageScan");
        
        // Initialize buffers asynchronously
        let init_encoder = command_buffer.new_compute_command_encoder();
        init_encoder.set_compute_pipeline_state(&self.init_pipeline);
        init_encoder.set_buffer(0, Some(&self.opportunity_count_buffer), 0);
        init_encoder.set_buffer(1, Some(&self.opportunities_buffer), 0);
        init_encoder.dispatch_thread_groups(MTLSize::new(1, 1, 1), MTLSize::new(1, 1, 1));
        init_encoder.end_encoding();
        
        // Execute ultra-fast arbitrage scanning
        let compute_encoder = command_buffer.new_compute_command_encoder();
        compute_encoder.set_label("UltraFastScan");
        compute_encoder.set_compute_pipeline_state(&self.compute_pipeline);
        
        // Set buffers
        compute_encoder.set_buffer(0, Some(&self.price_buffer), 0);
        compute_encoder.set_buffer(1, Some(&self.opportunity_count_buffer), 0);
        compute_encoder.set_buffer(2, Some(&self.opportunities_buffer), 0);
        
        // Set constants with optimal data types
        let price_count = num_prices as u32;
        let min_profit = 0.0005f32; // 0.05%
        
        compute_encoder.set_bytes(3, mem::size_of::<u32>() as u64, 
            &price_count as *const u32 as *const std::ffi::c_void);
        compute_encoder.set_bytes(4, mem::size_of::<f32>() as u64, 
            &min_profit as *const f32 as *const std::ffi::c_void);
        
        // Dispatch with optimized thread configuration
        let actual_thread_groups = MTLSize::new(
            (num_prices + 31) / 32,
            (num_prices + 31) / 32,
            1
        );
        
        compute_encoder.dispatch_thread_groups(actual_thread_groups, self.threadgroup_size);
        compute_encoder.end_encoding();
        
        // Execute with maximum priority
        command_buffer.commit();
        command_buffer.wait_until_completed(); // Synchronous for timing accuracy
        
        let scan_duration = scan_start.elapsed();
        let scan_time_us = scan_duration.as_micros() as u64;
        
        // Read results
        let opportunity_count = unsafe {
            let ptr = self.opportunity_count_buffer.contents() as *const u32;
            *ptr as u64
        };
        
        // Performance logging
        if scan_time_us < 10 {
            info!("🎯 TARGET ACHIEVED: {}μs scan time!", scan_time_us);
        } else if scan_time_us < 50 {
            info!("🔥 ULTRA-FAST: {}μs scan time (target: <10μs)", scan_time_us);
        } else {
            debug!("⚡ GPU scan: {}μs | {} opportunities", scan_time_us, opportunity_count);
        }
        
        Ok((opportunity_count, scan_time_us))
    }
    
    fn exchange_to_id(&self, exchange: &str) -> u16 {
        match exchange {
            "coinbase" => 1,
            "kraken" => 2,
            "kucoin" => 3,
            "binance" => 4,
            "gate_io" => 5,
            "mexc" => 6,
            "bitget" => 7,
            "okx" => 8,
            _ => 999,
        }
    }
    
    fn coin_to_id(&self, coin: &str) -> u16 {
        match coin {
            "BTC" => 1,
            "ETH" => 2,
            "ADA" => 3,
            "SOL" => 4,
            "MATIC" => 5,
            "LINK" => 6,
            "UNI" => 7,
            "AAVE" => 8,
            _ => 999,
        }
    }
    
    pub fn get_gpu_info(&self) -> String {
        format!("Ultra-Optimized M1 GPU: {} | Target: <10μs", self.device.name())
    }
}
