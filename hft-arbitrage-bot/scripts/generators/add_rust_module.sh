#!/bin/bash
# Ultra-advanced Rust module generator

MODULE_NAME=$1
MODULE_TYPE=${2:-"engine"}

if [ -z "$MODULE_NAME" ]; then
    echo "Usage: ./add_rust_module.sh <module_name> [engine|connector|strategy|ml_model]"
    exit 1
fi

echo "🦀 Generating advanced Rust module: $MODULE_NAME ($MODULE_TYPE)"

case $MODULE_TYPE in
    "engine")
        TEMPLATE="engine_template.rs"
        ;;
    "connector")
        TEMPLATE="connector_template.rs"
        ;;
    "strategy")
        TEMPLATE="strategy_template.rs"
        ;;
    "ml_model")
        TEMPLATE="ml_model_template.rs"
        ;;
    *)
        TEMPLATE="generic_template.rs"
        ;;
esac

# Generate from template
cat > "src/${MODULE_NAME}.rs" << RUST_EOF
//! ${MODULE_NAME} module for Ultra-HFT Arbitrage System
//! Advanced ${MODULE_TYPE} implementation with maximum performance optimization

use anyhow::Result;
use async_trait::async_trait;
use dashmap::DashMap;
use parking_lot::RwLock;
use serde::{Serialize, Deserialize};
use std::sync::{Arc, atomic::{AtomicU64, Ordering}};
use tokio::sync::Mutex;
use tracing::{info, warn, error, debug, instrument};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ${MODULE_NAME^}Config {
    pub enabled: bool,
    pub performance_target_ns: u64,
    pub max_concurrent_operations: usize,
}

impl Default for ${MODULE_NAME^}Config {
    fn default() -> Self {
        Self {
            enabled: true,
            performance_target_ns: 100_000, // 100μs target
            max_concurrent_operations: 1000,
        }
    }
}

pub struct ${MODULE_NAME^} {
    config: ${MODULE_NAME^}Config,
    metrics: Arc<Metrics>,
    state: Arc<RwLock<State>>,
}

#[derive(Debug, Default)]
struct Metrics {
    operations_count: AtomicU64,
    total_time_ns: AtomicU64,
    errors_count: AtomicU64,
}

#[derive(Debug, Default)]
struct State {
    is_running: bool,
    last_operation_time: Option<std::time::Instant>,
}

impl ${MODULE_NAME^} {
    pub fn new(config: ${MODULE_NAME^}Config) -> Self {
        Self {
            config,
            metrics: Arc::new(Metrics::default()),
            state: Arc::new(RwLock::new(State::default())),
        }
    }
    
    #[instrument(skip(self))]
    pub async fn initialize(&self) -> Result<()> {
        info!("🚀 Initializing {} with ultra-high performance", stringify!($MODULE_NAME));
        
        let mut state = self.state.write();
        state.is_running = true;
        
        info!("✅ {} initialized successfully", stringify!($MODULE_NAME));
        Ok(())
    }
    
    #[instrument(skip(self))]
    pub async fn execute(&self) -> Result<()> {
        let start = std::time::Instant::now();
        
        // Main logic here
        self.core_logic().await?;
        
        let elapsed_ns = start.elapsed().as_nanos() as u64;
        
        // Update metrics
        self.metrics.operations_count.fetch_add(1, Ordering::Relaxed);
        self.metrics.total_time_ns.fetch_add(elapsed_ns, Ordering::Relaxed);
        
        if elapsed_ns > self.config.performance_target_ns {
            warn!("Operation took {}ns, target: {}ns", elapsed_ns, self.config.performance_target_ns);
        }
        
        Ok(())
    }
    
    async fn core_logic(&self) -> Result<()> {
        // TODO: Implement core logic for ${MODULE_NAME}
        Ok(())
    }
    
    pub fn get_performance_metrics(&self) -> PerformanceMetrics {
        let ops = self.metrics.operations_count.load(Ordering::Relaxed);
        let total_time = self.metrics.total_time_ns.load(Ordering::Relaxed);
        let errors = self.metrics.errors_count.load(Ordering::Relaxed);
        
        PerformanceMetrics {
            operations_per_second: if total_time > 0 { ops * 1_000_000_000 / total_time } else { 0 },
            avg_execution_time_ns: if ops > 0 { total_time / ops } else { 0 },
            error_rate: if ops > 0 { errors as f64 / ops as f64 } else { 0.0 },
            total_operations: ops,
        }
    }
}

#[derive(Debug, Serialize)]
pub struct PerformanceMetrics {
    pub operations_per_second: u64,
    pub avg_execution_time_ns: u64,
    pub error_rate: f64,
    pub total_operations: u64,
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_${MODULE_NAME}_performance() {
        let config = ${MODULE_NAME^}Config::default();
        let module = ${MODULE_NAME^}::new(config);
        
        assert!(module.initialize().await.is_ok());
        
        let start = std::time::Instant::now();
        assert!(module.execute().await.is_ok());
        let duration = start.elapsed();
        
        // Should complete in under 100μs
        assert!(duration.as_micros() < 100);
    }
}
RUST_EOF

# Add to main.rs if not already present
if ! grep -q "mod $MODULE_NAME;" src/main.rs; then
    sed -i "/mod dynamic_arbitrage;/a mod $MODULE_NAME;" src/main.rs
fi

echo "✅ Created src/${MODULE_NAME}.rs"
echo "🔗 Added to main.rs imports"
