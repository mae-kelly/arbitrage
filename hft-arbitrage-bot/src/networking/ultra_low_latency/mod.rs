//! Ultra-low latency networking optimizations

use std::net::{SocketAddr, UdpSocket};
use std::os::unix::io::{AsRawFd, RawFd};
use anyhow::Result;

pub struct UltraLowLatencySocket {
    socket: UdpSocket,
    fd: RawFd,
}

impl UltraLowLatencySocket {
    pub fn new(bind_addr: SocketAddr) -> Result<Self> {
        let socket = UdpSocket::bind(bind_addr)?;
        let fd = socket.as_raw_fd();
        
        // Set socket options for ultra-low latency
        unsafe {
            // Set CPU affinity to specific core
            Self::set_cpu_affinity(fd, 0)?;
            
            // Disable Nagle's algorithm
            Self::set_tcp_nodelay(fd)?;
            
            // Set high priority
            Self::set_priority(fd, 7)?;
            
            // Enable SO_REUSEPORT for better distribution
            Self::set_reuseport(fd)?;
            
            // Set large socket buffers
            Self::set_socket_buffers(fd, 16 * 1024 * 1024)?;
            
            // Set real-time scheduling
            Self::set_realtime_priority()?;
        }
        
        Ok(Self { socket, fd })
    }
    
    unsafe fn set_cpu_affinity(fd: RawFd, cpu: usize) -> Result<()> {
        let mut cpu_set: libc::cpu_set_t = std::mem::zeroed();
        libc::CPU_SET(cpu, &mut cpu_set);
        
        let result = libc::sched_setaffinity(
            0,
            std::mem::size_of::<libc::cpu_set_t>(),
            &cpu_set,
        );
        
        if result != 0 {
            return Err(anyhow::anyhow!("Failed to set CPU affinity"));
        }
        
        Ok(())
    }
    
    unsafe fn set_tcp_nodelay(fd: RawFd) -> Result<()> {
        let flag = 1i32;
        let result = libc::setsockopt(
            fd,
            libc::IPPROTO_TCP,
            libc::TCP_NODELAY,
            &flag as *const _ as *const libc::c_void,
            std::mem::size_of::<i32>() as libc::socklen_t,
        );
        
        if result != 0 {
            return Err(anyhow::anyhow!("Failed to set TCP_NODELAY"));
        }
        
        Ok(())
    }
    
    unsafe fn set_priority(fd: RawFd, priority: i32) -> Result<()> {
        let result = libc::setsockopt(
            fd,
            libc::SOL_SOCKET,
            libc::SO_PRIORITY,
            &priority as *const _ as *const libc::c_void,
            std::mem::size_of::<i32>() as libc::socklen_t,
        );
        
        if result != 0 {
            return Err(anyhow::anyhow!("Failed to set socket priority"));
        }
        
        Ok(())
    }
    
    unsafe fn set_reuseport(fd: RawFd) -> Result<()> {
        let flag = 1i32;
        let result = libc::setsockopt(
            fd,
            libc::SOL_SOCKET,
            libc::SO_REUSEPORT,
            &flag as *const _ as *const libc::c_void,
            std::mem::size_of::<i32>() as libc::socklen_t,
        );
        
        if result != 0 {
            return Err(anyhow::anyhow!("Failed to set SO_REUSEPORT"));
        }
        
        Ok(())
    }
    
    unsafe fn set_socket_buffers(fd: RawFd, size: i32) -> Result<()> {
        // Set receive buffer
        let result = libc::setsockopt(
            fd,
            libc::SOL_SOCKET,
            libc::SO_RCVBUF,
            &size as *const _ as *const libc::c_void,
            std::mem::size_of::<i32>() as libc::socklen_t,
        );
        
        if result != 0 {
            return Err(anyhow::anyhow!("Failed to set SO_RCVBUF"));
        }
        
        // Set send buffer
        let result = libc::setsockopt(
            fd,
            libc::SOL_SOCKET,
            libc::SO_SNDBUF,
            &size as *const _ as *const libc::c_void,
            std::mem::size_of::<i32>() as libc::socklen_t,
        );
        
        if result != 0 {
            return Err(anyhow::anyhow!("Failed to set SO_SNDBUF"));
        }
        
        Ok(())
    }
    
    unsafe fn set_realtime_priority() -> Result<()> {
        let param = libc::sched_param {
            sched_priority: 99, // Highest real-time priority
        };
        
        let result = libc::sched_setscheduler(
            0,
            libc::SCHED_FIFO,
            &param,
        );
        
        if result != 0 {
            // Don't fail if we can't set RT priority (needs root)
            eprintln!("Warning: Could not set real-time priority (needs root)");
        }
        
        Ok(())
    }
    
    pub fn send_with_timestamp(&self, data: &[u8], addr: SocketAddr) -> Result<u64> {
        let start = std::time::Instant::now();
        self.socket.send_to(data, addr)?;
        Ok(start.elapsed().as_nanos() as u64)
    }
    
    pub fn recv_with_timestamp(&self, buf: &mut [u8]) -> Result<(usize, SocketAddr, u64)> {
        let start = std::time::Instant::now();
        let (size, addr) = self.socket.recv_from(buf)?;
        let latency = start.elapsed().as_nanos() as u64;
        Ok((size, addr, latency))
    }
}

/// DPDK-style packet processing (simulation)
pub struct PacketProcessor {
    packet_buffer: Vec<Packet>,
    batch_size: usize,
}

#[derive(Debug, Clone)]
pub struct Packet {
    pub data: Vec<u8>,
    pub timestamp: u64,
    pub source: SocketAddr,
}

impl PacketProcessor {
    pub fn new(batch_size: usize) -> Self {
        Self {
            packet_buffer: Vec::with_capacity(batch_size),
            batch_size,
        }
    }
    
    pub fn process_batch(&mut self, packets: Vec<Packet>) -> Vec<ProcessedPacket> {
        let mut results = Vec::with_capacity(packets.len());
        
        // Process in batches for better cache efficiency
        for chunk in packets.chunks(self.batch_size) {
            for packet in chunk {
                results.push(self.process_single_packet(packet));
            }
        }
        
        results
    }
    
    fn process_single_packet(&self, packet: &Packet) -> ProcessedPacket {
        // Simulate market data parsing
        let processing_start = std::time::Instant::now();
        
        // Parse market data (simplified)
        let parsed_data = if packet.data.len() > 8 {
            // Extract price data
            let price = f64::from_le_bytes([
                packet.data[0], packet.data[1], packet.data[2], packet.data[3],
                packet.data[4], packet.data[5], packet.data[6], packet.data[7],
            ]);
            Some(price)
        } else {
            None
        };
        
        ProcessedPacket {
            original: packet.clone(),
            parsed_price: parsed_data,
            processing_time_ns: processing_start.elapsed().as_nanos() as u64,
        }
    }
}

#[derive(Debug, Clone)]
pub struct ProcessedPacket {
    pub original: Packet,
    pub parsed_price: Option<f64>,
    pub processing_time_ns: u64,
}
