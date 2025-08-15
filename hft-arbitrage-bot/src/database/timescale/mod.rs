use sqlx::{PgPool, Row};
use anyhow::Result;
use chrono::{DateTime, Utc};
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone)]
pub struct TimescaleManager {
    pool: PgPool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PerformanceMetrics {
    pub timestamp: DateTime<Utc>,
    pub scan_time_us: i64,
    pub opportunities_found: i32,
    pub profit_potential: f64,
    pub gas_price_gwei: f64,
    pub success_rate: f32,
}

impl TimescaleManager {
    pub async fn new(database_url: &str) -> Result<Self> {
        let pool = PgPool::connect(database_url).await?;
        
        // Create hypertables
        sqlx::query!(
            "SELECT create_hypertable('performance_metrics', 'timestamp', if_not_exists => TRUE)"
        )
        .execute(&pool)
        .await
        .ok(); // Ignore if already exists
        
        Ok(Self { pool })
    }
    
    pub async fn insert_performance_metric(&self, metric: &PerformanceMetrics) -> Result<()> {
        sqlx::query!(
            r#"
            INSERT INTO performance_metrics (timestamp, scan_time_us, opportunities_found, 
                                           profit_potential, gas_price_gwei, success_rate)
            VALUES ($1, $2, $3, $4, $5, $6)
            "#,
            metric.timestamp,
            metric.scan_time_us,
            metric.opportunities_found,
            metric.profit_potential,
            metric.gas_price_gwei,
            metric.success_rate
        )
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }
    
    pub async fn get_performance_trend(&self, hours: i32) -> Result<Vec<PerformanceMetrics>> {
        let results = sqlx::query!(
            r#"
            SELECT timestamp, scan_time_us, opportunities_found, profit_potential, 
                   gas_price_gwei, success_rate
            FROM performance_metrics
            WHERE timestamp > NOW() - INTERVAL '%1 hours'
            ORDER BY timestamp DESC
            "#,
            hours
        )
        .fetch_all(&self.pool)
        .await?;
        
        let metrics: Vec<PerformanceMetrics> = results.into_iter()
            .map(|row| PerformanceMetrics {
                timestamp: row.timestamp,
                scan_time_us: row.scan_time_us,
                opportunities_found: row.opportunities_found,
                profit_potential: row.profit_potential,
                gas_price_gwei: row.gas_price_gwei,
                success_rate: row.success_rate,
            })
            .collect();
        
        Ok(metrics)
    }
    
    pub async fn get_aggregated_stats(&self, hours: i32) -> Result<AggregatedStats> {
        let result = sqlx::query!(
            r#"
            SELECT 
                AVG(scan_time_us) as avg_scan_time,
                MIN(scan_time_us) as min_scan_time,
                MAX(scan_time_us) as max_scan_time,
                SUM(opportunities_found) as total_opportunities,
                AVG(profit_potential) as avg_profit_potential,
                AVG(success_rate) as avg_success_rate
            FROM performance_metrics
            WHERE timestamp > NOW() - INTERVAL '%1 hours'
            "#,
            hours
        )
        .fetch_one(&self.pool)
        .await?;
        
        Ok(AggregatedStats {
            avg_scan_time_us: result.avg_scan_time.unwrap_or(0.0),
            min_scan_time_us: result.min_scan_time.unwrap_or(0),
            max_scan_time_us: result.max_scan_time.unwrap_or(0),
            total_opportunities: result.total_opportunities.unwrap_or(0),
            avg_profit_potential: result.avg_profit_potential.unwrap_or(0.0),
            avg_success_rate: result.avg_success_rate.unwrap_or(0.0),
        })
    }
}

#[derive(Debug, Serialize)]
pub struct AggregatedStats {
    pub avg_scan_time_us: f64,
    pub min_scan_time_us: i64,
    pub max_scan_time_us: i64,
    pub total_opportunities: i64,
    pub avg_profit_potential: f64,
    pub avg_success_rate: f32,
}
