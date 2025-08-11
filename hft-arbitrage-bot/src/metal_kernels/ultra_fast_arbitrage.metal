#include <metal_stdlib>
using namespace metal;

// Ultra-optimized price structure for maximum GPU throughput
struct UltraPrice {
    packed_float2 bid_ask;    // Pack bid/ask into single 64-bit load
    packed_float2 vol_time;   // Pack volume/timestamp
    uint32_t exchange_coin;   // Pack exchange_id and coin_id into single uint32
};

// Ultra-fast arbitrage scanning kernel - optimized for <10μs execution
kernel void ultra_fast_arbitrage_scan(
    device const UltraPrice* prices [[buffer(0)]],
    device atomic_uint* opportunity_count [[buffer(1)]],
    device uint2* opportunities [[buffer(2)]],
    constant uint& price_count [[buffer(3)]],
    constant float& min_profit [[buffer(4)]],
    uint2 gid [[thread_position_in_grid]],
    uint2 threads_per_grid [[threads_per_grid]]
) {
    uint idx1 = gid.x;
    uint idx2 = gid.y;
    
    // Bounds check with early return
    if (idx1 >= price_count || idx2 >= price_count || idx1 == idx2) return;
    
    // Load prices with single memory access
    UltraPrice p1 = prices[idx1];
    UltraPrice p2 = prices[idx2];
    
    // Extract coin IDs with bit operations (ultra-fast)
    uint coin1 = p1.exchange_coin & 0xFFFF;
    uint coin2 = p2.exchange_coin & 0xFFFF;
    uint exchange1 = p1.exchange_coin >> 16;
    uint exchange2 = p2.exchange_coin >> 16;
    
    // Only compare same coin, different exchanges
    if (coin1 != coin2 || exchange1 == exchange2) return;
    
    // Extract bid/ask with SIMD operations
    float2 ba1 = p1.bid_ask;
    float2 ba2 = p2.bid_ask;
    
    // Ultra-fast profit calculation with SIMD
    float profit1 = (ba2.x - ba1.y) / ba1.y; // p2.bid - p1.ask
    float profit2 = (ba1.x - ba2.y) / ba2.y; // p1.bid - p2.ask
    
    // Check both directions simultaneously
    bool profitable1 = profit1 >= min_profit && ba1.y > 0.0f;
    bool profitable2 = profit2 >= min_profit && ba2.y > 0.0f;
    
    if (profitable1 || profitable2) {
        uint opp_idx = atomic_fetch_add_explicit(opportunity_count, 1, memory_order_relaxed);
        if (opp_idx < 10000) { // Max opportunities
            if (profitable1) {
                opportunities[opp_idx] = uint2(idx1, idx2);
            } else {
                opportunities[opp_idx] = uint2(idx2, idx1);
            }
        }
    }
}

// Pre-allocated buffer initialization kernel
kernel void initialize_buffers(
    device atomic_uint* opportunity_count [[buffer(0)]],
    device uint2* opportunities [[buffer(1)]],
    uint gid [[thread_position_in_grid]]
) {
    if (gid == 0) {
        atomic_store_explicit(opportunity_count, 0, memory_order_relaxed);
    }
    if (gid < 10000) {
        opportunities[gid] = uint2(0, 0);
    }
}
