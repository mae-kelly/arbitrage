use sqlx::{PgPool, Row};
use anyhow::Result;
use serde::{Serialize, Deserialize};
use uuid::Uuid;
use chrono::{DateTime, Utc};

#[derive(Debug, Clone)]
pub struct DatabaseManager {
    pool: PgPool,
}

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct ExecutionRecord {
    pub id: Uuid,
    pub opportunity_id: String,
    pub symbol: String,
    pub buy_exchange: String,
    pub sell_exchange: String,
    pub buy_price: f64,
    pub sell_price: f64,
    pub profit_usd: f64,
    pub gas_cost: f64,
    pub execution_time_ms: i64,
    pub success: bool,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct PriceRecord {
    pub id: Uuid,
    pub exchange: String,
    pub symbol: String,
    pub price: f64,
    pub bid: f64,
    pub ask: f64,
    pub volume: f64,
    pub timestamp: DateTime<Utc>,
}

impl DatabaseManager {
    pub async fn new(database_url: &str) -> Result<Self> {
        let pool = PgPool::connect(database_url).await?;
        sqlx::migrate!("./migrations").run(&pool).await?;
        
        Ok(Self { pool })
    }
    
    pub async fn store_execution(&self, record: &ExecutionRecord) -> Result<()> {
        sqlx::query!(
            r#"
            INSERT INTO executions (id, opportunity_id, symbol, buy_exchange, sell_exchange, 
                                  buy_price, sell_price, profit_usd, gas_cost, execution_time_ms, 
                                  success, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            "#,
            record.id,
            record.opportunity_id,
            record.symbol,
            record.buy_exchange,
            record.sell_exchange,
            record.buy_price,
            record.sell_price,
            record.profit_usd,
            record.gas_cost,
            record.execution_time_ms,
            record.success,
            record.created_at
        )
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }
    
    pub async fn store_price(&self, record: &PriceRecord) -> Result<()> {
        sqlx::query!(
            r#"
            INSERT INTO prices (id, exchange, symbol, price, bid, ask, volume, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (exchange, symbol, timestamp) DO UPDATE SET
            price = EXCLUDED.price,
            bid = EXCLUDED.bid,
            ask = EXCLUDED.ask,
            volume = EXCLUDED.volume
            "#,
            record.id,
            record.exchange,
            record.symbol,
            record.price,
            record.bid,
            record.ask,
            record.volume,
            record.timestamp
        )
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }
    
    pub async fn get_profit_summary(&self, hours: i32) -> Result<f64> {
        let result = sqlx::query!(
            "SELECT COALESCE(SUM(profit_usd), 0) as total_profit 
             FROM executions 
             WHERE success = true AND created_at > NOW() - INTERVAL '%1 hours'",
            hours
        )
        .fetch_one(&self.pool)
        .await?;
        
        Ok(result.total_profit.unwrap_or(0.0))
    }
    
    pub async fn get_execution_analytics(&self) -> Result<ExecutionAnalytics> {
        let result = sqlx::query!(
            r#"
            SELECT 
                COUNT(*) as total_executions,
                COUNT(CASE WHEN success THEN 1 END) as successful_executions,
                AVG(profit_usd) as avg_profit,
                AVG(execution_time_ms) as avg_execution_time,
                SUM(profit_usd) as total_profit
            FROM executions 
            WHERE created_at > NOW() - INTERVAL '24 hours'
            "#
        )
        .fetch_one(&self.pool)
        .await?;
        
        Ok(ExecutionAnalytics {
            total_executions: result.total_executions.unwrap_or(0),
            successful_executions: result.successful_executions.unwrap_or(0),
            success_rate: if result.total_executions.unwrap_or(0) > 0 {
                result.successful_executions.unwrap_or(0) as f64 / result.total_executions.unwrap_or(1) as f64
            } else { 0.0 },
            avg_profit: result.avg_profit.unwrap_or(0.0),
            avg_execution_time_ms: result.avg_execution_time.unwrap_or(0.0),
            total_profit: result.total_profit.unwrap_or(0.0),
        })
    }
}

#[derive(Debug, Serialize)]
pub struct ExecutionAnalytics {
    pub total_executions: i64,
    pub successful_executions: i64,
    pub success_rate: f64,
    pub avg_profit: f64,
    pub avg_execution_time_ms: f64,
    pub total_profit: f64,
}
