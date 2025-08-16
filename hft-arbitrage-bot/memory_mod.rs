//! Custom memory allocators for ultra-low latency

use std::alloc::{GlobalAlloc, Layout};
use std::sync::atomic::{AtomicPtr, AtomicUsize, Ordering};
use std::ptr;

/// Thread-local memory pool for hot path allocations
pub struct MemoryPool {
    free_blocks: AtomicPtr<Block>,
    block_size: usize,
    pool_size: usize,
    allocated_count: AtomicUsize,
}

struct Block {
    next: AtomicPtr<Block>,
    data: [u8; 0],
}

impl MemoryPool {
    pub fn new(block_size: usize, pool_size: usize) -> Self {
        let layout = Layout::from_size_align(
            block_size + std::mem::size_of::<Block>(),
            std::mem::align_of::<Block>(),
        ).unwrap();
        
        // Pre-allocate all blocks
        let mut free_blocks = ptr::null_mut();
        
        for _ in 0..pool_size {
            unsafe {
                let block = std::alloc::alloc(layout) as *mut Block;
                (*block).next = AtomicPtr::new(free_blocks);
                free_blocks = block;
            }
        }
        
        Self {
            free_blocks: AtomicPtr::new(free_blocks),
            block_size,
            pool_size,
            allocated_count: AtomicUsize::new(0),
        }
    }
    
    pub fn allocate(&self) -> Option<*mut u8> {
        loop {
            let head = self.free_blocks.load(Ordering::Acquire);
            if head.is_null() {
                return None; // Pool exhausted
            }
            
            let next = unsafe { (*head).next.load(Ordering::Relaxed) };
            
            match self.free_blocks.compare_exchange_weak(
                head,
                next,
                Ordering::Release,
                Ordering::Relaxed,
            ) {
                Ok(_) => {
                    self.allocated_count.fetch_add(1, Ordering::Relaxed);
                    return Some(unsafe { head.add(1) as *mut u8 });
                }
                Err(_) => continue,
            }
        }
    }
    
    pub fn deallocate(&self, ptr: *mut u8) {
        if ptr.is_null() {
            return;
        }
        
        let block = unsafe { (ptr as *mut Block).sub(1) };
        
        loop {
            let head = self.free_blocks.load(Ordering::Acquire);
            unsafe { (*block).next.store(head, Ordering::Relaxed) };
            
            match self.free_blocks.compare_exchange_weak(
                head,
                block,
                Ordering::Release,
                Ordering::Relaxed,
            ) {
                Ok(_) => {
                    self.allocated_count.fetch_sub(1, Ordering::Relaxed);
                    break;
                }
                Err(_) => continue,
            }
        }
    }
    
    pub fn allocated_count(&self) -> usize {
        self.allocated_count.load(Ordering::Relaxed)
    }
    
    pub fn utilization(&self) -> f64 {
        self.allocated_count() as f64 / self.pool_size as f64
    }
}

/// Custom allocator for trading structures
pub struct TradingAllocator {
    small_pool: MemoryPool,  // < 64 bytes
    medium_pool: MemoryPool, // 64-1024 bytes  
    large_pool: MemoryPool,  // > 1024 bytes
}

impl TradingAllocator {
    pub fn new() -> Self {
        Self {
            small_pool: MemoryPool::new(64, 10000),
            medium_pool: MemoryPool::new(1024, 5000),
            large_pool: MemoryPool::new(4096, 1000),
        }
    }
    
    pub fn allocate(&self, size: usize) -> Option<*mut u8> {
        if size <= 64 {
            self.small_pool.allocate()
        } else if size <= 1024 {
            self.medium_pool.allocate()
        } else if size <= 4096 {
            self.large_pool.allocate()
        } else {
            None // Use system allocator for very large allocations
        }
    }
    
    pub fn deallocate(&self, ptr: *mut u8, size: usize) {
        if size <= 64 {
            self.small_pool.deallocate(ptr);
        } else if size <= 1024 {
            self.medium_pool.deallocate(ptr);
        } else if size <= 4096 {
            self.large_pool.deallocate(ptr);
        }
    }
    
    pub fn get_stats(&self) -> PoolStats {
        PoolStats {
            small_utilization: self.small_pool.utilization(),
            medium_utilization: self.medium_pool.utilization(),
            large_utilization: self.large_pool.utilization(),
            total_allocated: self.small_pool.allocated_count() + 
                           self.medium_pool.allocated_count() + 
                           self.large_pool.allocated_count(),
        }
    }
}

#[derive(Debug)]
pub struct PoolStats {
    pub small_utilization: f64,
    pub medium_utilization: f64,
    pub large_utilization: f64,
    pub total_allocated: usize,
}

thread_local! {
    static TRADING_ALLOCATOR: TradingAllocator = TradingAllocator::new();
}

/// Fast allocate for trading hot paths
pub fn fast_alloc(size: usize) -> Option<*mut u8> {
    TRADING_ALLOCATOR.with(|allocator| allocator.allocate(size))
}

/// Fast deallocate for trading hot paths
pub fn fast_dealloc(ptr: *mut u8, size: usize) {
    TRADING_ALLOCATOR.with(|allocator| allocator.deallocate(ptr, size));
}

/// Get memory pool statistics
pub fn get_pool_stats() -> PoolStats {
    TRADING_ALLOCATOR.with(|allocator| allocator.get_stats())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;
    
    #[test]
    fn test_memory_pool_performance() {
        let pool = MemoryPool::new(1024, 1000);
        
        let start = std::time::Instant::now();
        
        // Allocate and deallocate rapidly
        for _ in 0..100000 {
            if let Some(ptr) = pool.allocate() {
                pool.deallocate(ptr);
            }
        }
        
        let duration = start.elapsed();
        println!("Memory pool: 100k alloc/dealloc in {}μs", duration.as_micros());
        
        assert!(duration.as_millis() < 50); // Should be very fast
        assert_eq!(pool.allocated_count(), 0); // All freed
    }
    
    #[test]
    fn test_concurrent_memory_pool() {
        let pool = std::sync::Arc::new(MemoryPool::new(64, 10000));
        let mut handles = Vec::new();
        
        for _ in 0..8 {
            let pool_clone = pool.clone();
            handles.push(thread::spawn(move || {
                for _ in 0..10000 {
                    if let Some(ptr) = pool_clone.allocate() {
                        // Simulate some work
                        std::thread::yield_now();
                        pool_clone.deallocate(ptr);
                    }
                }
            }));
        }
        
        for handle in handles {
            handle.join().unwrap();
        }
        
        assert_eq!(pool.allocated_count(), 0);
    }
}
