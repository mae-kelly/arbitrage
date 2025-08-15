//! Lock-free data structures for maximum concurrency

use std::sync::atomic::{AtomicPtr, AtomicUsize, Ordering};
use std::ptr;
use std::alloc::{alloc, dealloc, Layout};

/// Lock-free ring buffer for high-frequency price updates
pub struct LockFreeRingBuffer<T> {
    buffer: AtomicPtr<T>,
    capacity: usize,
    write_pos: AtomicUsize,
    read_pos: AtomicUsize,
}

impl<T> LockFreeRingBuffer<T> 
where
    T: Copy + Send + Sync,
{
    pub fn new(capacity: usize) -> Self {
        let layout = Layout::array::<T>(capacity).unwrap();
        let buffer = unsafe { alloc(layout) as *mut T };
        
        Self {
            buffer: AtomicPtr::new(buffer),
            capacity,
            write_pos: AtomicUsize::new(0),
            read_pos: AtomicUsize::new(0),
        }
    }
    
    pub fn push(&self, item: T) -> bool {
        let write_pos = self.write_pos.load(Ordering::Relaxed);
        let read_pos = self.read_pos.load(Ordering::Acquire);
        let next_write = (write_pos + 1) % self.capacity;
        
        if next_write == read_pos {
            return false; // Buffer full
        }
        
        unsafe {
            let buffer = self.buffer.load(Ordering::Relaxed);
            ptr::write(buffer.add(write_pos), item);
        }
        
        self.write_pos.store(next_write, Ordering::Release);
        true
    }
    
    pub fn pop(&self) -> Option<T> {
        let read_pos = self.read_pos.load(Ordering::Relaxed);
        let write_pos = self.write_pos.load(Ordering::Acquire);
        
        if read_pos == write_pos {
            return None; // Buffer empty
        }
        
        let item = unsafe {
            let buffer = self.buffer.load(Ordering::Relaxed);
            ptr::read(buffer.add(read_pos))
        };
        
        let next_read = (read_pos + 1) % self.capacity;
        self.read_pos.store(next_read, Ordering::Release);
        
        Some(item)
    }
    
    pub fn len(&self) -> usize {
        let write_pos = self.write_pos.load(Ordering::Acquire);
        let read_pos = self.read_pos.load(Ordering::Acquire);
        
        if write_pos >= read_pos {
            write_pos - read_pos
        } else {
            self.capacity - read_pos + write_pos
        }
    }
    
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
    
    pub fn is_full(&self) -> bool {
        self.len() == self.capacity - 1
    }
}

impl<T> Drop for LockFreeRingBuffer<T> {
    fn drop(&mut self) {
        let buffer = self.buffer.load(Ordering::Relaxed);
        if !buffer.is_null() {
            let layout = Layout::array::<T>(self.capacity).unwrap();
            unsafe { dealloc(buffer as *mut u8, layout) };
        }
    }
}

/// Lock-free hash map for price lookups
pub struct LockFreeHashMap<K, V> {
    buckets: Vec<AtomicPtr<Node<K, V>>>,
    bucket_count: usize,
}

struct Node<K, V> {
    key: K,
    value: V,
    next: AtomicPtr<Node<K, V>>,
}

impl<K, V> LockFreeHashMap<K, V>
where
    K: Eq + std::hash::Hash + Clone,
    V: Clone,
{
    pub fn new(bucket_count: usize) -> Self {
        let mut buckets = Vec::with_capacity(bucket_count);
        for _ in 0..bucket_count {
            buckets.push(AtomicPtr::new(ptr::null_mut()));
        }
        
        Self {
            buckets,
            bucket_count,
        }
    }
    
    fn hash(&self, key: &K) -> usize {
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        std::hash::Hash::hash(key, &mut hasher);
        std::hash::Hasher::finish(&hasher) as usize % self.bucket_count
    }
    
    pub fn insert(&self, key: K, value: V) -> bool {
        let bucket_idx = self.hash(&key);
        let bucket = &self.buckets[bucket_idx];
        
        let new_node = Box::into_raw(Box::new(Node {
            key: key.clone(),
            value,
            next: AtomicPtr::new(ptr::null_mut()),
        }));
        
        loop {
            let head = bucket.load(Ordering::Acquire);
            unsafe { (*new_node).next.store(head, Ordering::Relaxed) };
            
            match bucket.compare_exchange_weak(
                head,
                new_node,
                Ordering::Release,
                Ordering::Relaxed,
            ) {
                Ok(_) => return true,
                Err(_) => continue,
            }
        }
    }
    
    pub fn get(&self, key: &K) -> Option<V> {
        let bucket_idx = self.hash(key);
        let bucket = &self.buckets[bucket_idx];
        
        let mut current = bucket.load(Ordering::Acquire);
        
        while !current.is_null() {
            unsafe {
                if (*current).key == *key {
                    return Some((*current).value.clone());
                }
                current = (*current).next.load(Ordering::Acquire);
            }
        }
        
        None
    }
}

/// Lock-free queue for high-frequency updates
pub struct LockFreeQueue<T> {
    head: AtomicPtr<QueueNode<T>>,
    tail: AtomicPtr<QueueNode<T>>,
}

struct QueueNode<T> {
    data: Option<T>,
    next: AtomicPtr<QueueNode<T>>,
}

impl<T> LockFreeQueue<T> {
    pub fn new() -> Self {
        let dummy = Box::into_raw(Box::new(QueueNode {
            data: None,
            next: AtomicPtr::new(ptr::null_mut()),
        }));
        
        Self {
            head: AtomicPtr::new(dummy),
            tail: AtomicPtr::new(dummy),
        }
    }
    
    pub fn enqueue(&self, data: T) {
        let new_node = Box::into_raw(Box::new(QueueNode {
            data: Some(data),
            next: AtomicPtr::new(ptr::null_mut()),
        }));
        
        loop {
            let tail = self.tail.load(Ordering::Acquire);
            let next = unsafe { (*tail).next.load(Ordering::Acquire) };
            
            if tail == self.tail.load(Ordering::Acquire) {
                if next.is_null() {
                    match unsafe { (*tail).next.compare_exchange_weak(
                        next,
                        new_node,
                        Ordering::Release,
                        Ordering::Relaxed,
                    ) } {
                        Ok(_) => break,
                        Err(_) => continue,
                    }
                } else {
                    self.tail.compare_exchange_weak(
                        tail,
                        next,
                        Ordering::Release,
                        Ordering::Relaxed,
                    ).ok();
                }
            }
        }
        
        self.tail.compare_exchange_weak(
            self.tail.load(Ordering::Acquire),
            new_node,
            Ordering::Release,
            Ordering::Relaxed,
        ).ok();
    }
    
    pub fn dequeue(&self) -> Option<T> {
        loop {
            let head = self.head.load(Ordering::Acquire);
            let tail = self.tail.load(Ordering::Acquire);
            let next = unsafe { (*head).next.load(Ordering::Acquire) };
            
            if head == self.head.load(Ordering::Acquire) {
                if head == tail {
                    if next.is_null() {
                        return None;
                    }
                    self.tail.compare_exchange_weak(
                        tail,
                        next,
                        Ordering::Release,
                        Ordering::Relaxed,
                    ).ok();
                } else {
                    if next.is_null() {
                        continue;
                    }
                    
                    let data = unsafe { (*next).data.take() };
                    
                    match self.head.compare_exchange_weak(
                        head,
                        next,
                        Ordering::Release,
                        Ordering::Relaxed,
                    ) {
                        Ok(_) => {
                            unsafe { Box::from_raw(head) };
                            return data;
                        }
                        Err(_) => continue,
                    }
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;
    use std::sync::Arc;
    
    #[test]
    fn test_lockfree_ringbuffer_performance() {
        let buffer = Arc::new(LockFreeRingBuffer::new(10000));
        let buffer_clone = buffer.clone();
        
        let start = std::time::Instant::now();
        
        // Spawn producer thread
        let producer = thread::spawn(move || {
            for i in 0..100000 {
                while !buffer_clone.push(i) {
                    std::hint::spin_loop();
                }
            }
        });
        
        // Consumer in main thread
        let mut consumed = 0;
        while consumed < 100000 {
            if let Some(_) = buffer.pop() {
                consumed += 1;
            } else {
                std::hint::spin_loop();
            }
        }
        
        producer.join().unwrap();
        let duration = start.elapsed();
        
        println!("Lock-free buffer: 100k operations in {}μs", duration.as_micros());
        assert!(duration.as_millis() < 100); // Should complete in under 100ms
    }
}
