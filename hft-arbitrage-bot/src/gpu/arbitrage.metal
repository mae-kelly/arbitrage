#include <metal_stdlib>
using namespace metal;

// Ultra-fast price comparison kernel for M1 GPU
kernel void compare_prices(
    device const float4* buy_prices [[buffer(0)]],
    device const float4* sell_prices [[buffer(1)]], 
    device float* profit_ratios [[buffer(2)]],
    device uint* opportunity_indices [[buffer(3)]],
    device atomic_uint* opportunity_count [[buffer(4)]],
    constant uint& num_pairs [[buffer(5)]],
    constant float& min_profit_threshold [[buffer(6)]],
    uint gid [[thread_position_in_grid]]
) {
    if (gid >= num_pairs) return;
    
    // Load prices (bid, ask, volume, timestamp)
    float4 buy = buy_prices[gid];
    float4 sell = sell_prices[gid];
    
    // Calculate profit ratio: (sell_bid - buy_ask) / buy_ask
    float profit_ratio = (sell.x - buy.y) / buy.y;
    profit_ratios[gid] = profit_ratio;
    
    // Check if profitable and record opportunity
    if (profit_ratio > min_profit_threshold && buy.y > 0.0f && sell.x > buy.y) {
        uint index = atomic_fetch_add_explicit(opportunity_count, 1, memory_order_relaxed);
        if (index < 10000) { // Max opportunities buffer
            opportunity_indices[index] = gid;
        }
    }
}

// Parallel sorting for top opportunities
kernel void sort_opportunities(
    device float* profit_ratios [[buffer(0)]],
    device uint* indices [[buffer(1)]],
    constant uint& count [[buffer(2)]],
    uint gid [[thread_position_in_grid]]
) {
    // Bitonic sort implementation for GPU
    for (uint k = 2; k <= count; k <<= 1) {
        for (uint j = k >> 1; j > 0; j >>= 1) {
            uint ixj = gid ^ j;
            if (ixj > gid && gid < count && ixj < count) {
                if ((gid & k) == 0) {
                    if (profit_ratios[indices[gid]] < profit_ratios[indices[ixj]]) {
                        uint temp = indices[gid];
                        indices[gid] = indices[ixj];
                        indices[ixj] = temp;
                    }
                } else {
                    if (profit_ratios[indices[gid]] > profit_ratios[indices[ixj]]) {
                        uint temp = indices[gid];
                        indices[gid] = indices[ixj];
                        indices[ixj] = temp;
                    }
                }
            }
            threadgroup_barrier(mem_flags::mem_threadgroup);
        }
    }
}

// Flash loan profitability calculation
kernel void calculate_flash_profits(
    device const float* profit_ratios [[buffer(0)]],
    device const float* trade_sizes [[buffer(1)]],
    device const float* gas_costs [[buffer(2)]],
    device float* net_profits [[buffer(3)]],
    constant float& flash_loan_fee_bps [[buffer(4)]],
    uint gid [[thread_position_in_grid]]
) {
    float gross_profit = profit_ratios[gid] * trade_sizes[gid];
    float flash_fee = trade_sizes[gid] * flash_loan_fee_bps / 10000.0f;
    float exchange_fees = trade_sizes[gid] * 0.002f; // 0.2% total
    
    net_profits[gid] = gross_profit - flash_fee - gas_costs[gid] - exchange_fees;
}
