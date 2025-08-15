-- Initial database schema

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- Executions table
CREATE TABLE executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    opportunity_id VARCHAR NOT NULL,
    symbol VARCHAR NOT NULL,
    buy_exchange VARCHAR NOT NULL,
    sell_exchange VARCHAR NOT NULL,
    buy_price DECIMAL(20,8) NOT NULL,
    sell_price DECIMAL(20,8) NOT NULL,
    profit_usd DECIMAL(20,8) NOT NULL,
    gas_cost DECIMAL(20,8) NOT NULL,
    execution_time_ms BIGINT NOT NULL,
    success BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_executions_created_at ON executions(created_at);
CREATE INDEX idx_executions_symbol ON executions(symbol);
CREATE INDEX idx_executions_success ON executions(success);

-- Prices table with unique constraint
CREATE TABLE prices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exchange VARCHAR NOT NULL,
    symbol VARCHAR NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    bid DECIMAL(20,8) NOT NULL,
    ask DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    UNIQUE(exchange, symbol, timestamp)
);

CREATE INDEX idx_prices_timestamp ON prices(timestamp);
CREATE INDEX idx_prices_exchange_symbol ON prices(exchange, symbol);

-- Performance metrics table (TimescaleDB hypertable)
CREATE TABLE performance_metrics (
    timestamp TIMESTAMPTZ NOT NULL,
    scan_time_us BIGINT NOT NULL,
    opportunities_found INTEGER NOT NULL,
    profit_potential DECIMAL(20,8) NOT NULL,
    gas_price_gwei DECIMAL(10,2) NOT NULL,
    success_rate REAL NOT NULL
);

-- Convert to hypertable (will be done in TimescaleManager)
