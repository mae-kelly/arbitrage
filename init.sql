CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    tx_hash VARCHAR(66) UNIQUE NOT NULL,
    block_number BIGINT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    token_in VARCHAR(42) NOT NULL,
    token_out VARCHAR(42) NOT NULL,
    amount_in NUMERIC(78, 0) NOT NULL,
    amount_out NUMERIC(78, 0) NOT NULL,
    dex_buy VARCHAR(50) NOT NULL,
    dex_sell VARCHAR(50) NOT NULL,
    gas_used NUMERIC(78, 0),
    gas_price NUMERIC(78, 0) NOT NULL,
    profit_wei NUMERIC(78, 0) NOT NULL,
    profit_usd NUMERIC(20, 6),
    status VARCHAR(20) NOT NULL,
    mode VARCHAR(10) NOT NULL,
    confidence NUMERIC(5, 4),
    ml_prediction NUMERIC(5, 4),
    flash_loan_provider VARCHAR(20),
    flash_loan_fee NUMERIC(78, 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trades_timestamp ON trades(timestamp DESC);
CREATE INDEX idx_trades_profit ON trades(profit_wei DESC);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_tokens ON trades(token_in, token_out);
CREATE INDEX idx_trades_dex ON trades(dex_buy, dex_sell);

CREATE TABLE IF NOT EXISTS opportunities (
    id SERIAL PRIMARY KEY,
    discovered_at TIMESTAMP NOT NULL,
    token_in VARCHAR(42) NOT NULL,
    token_out VARCHAR(42) NOT NULL,
    amount_in NUMERIC(78, 0) NOT NULL,
    expected_profit NUMERIC(78, 0) NOT NULL,
    dex_buy VARCHAR(50) NOT NULL,
    dex_sell VARCHAR(50) NOT NULL,
    gas_price NUMERIC(78, 0) NOT NULL,
    confidence NUMERIC(5, 4),
    executed BOOLEAN DEFAULT FALSE,
    trade_id INTEGER REFERENCES trades(id),
    mempool_tx_hash VARCHAR(66),
    block_number BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_opportunities_discovered ON opportunities(discovered_at DESC);
CREATE INDEX idx_opportunities_executed ON opportunities(executed);
CREATE INDEX idx_opportunities_profit ON opportunities(expected_profit DESC);

CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    total_trades INTEGER NOT NULL,
    successful_trades INTEGER NOT NULL,
    failed_trades INTEGER NOT NULL,
    total_profit_wei NUMERIC(78, 0) NOT NULL,
    total_profit_usd NUMERIC(20, 6),
    total_gas_spent NUMERIC(78, 0) NOT NULL,
    avg_confidence NUMERIC(5, 4),
    avg_ml_prediction NUMERIC(5, 4),
    win_rate NUMERIC(5, 4),
    best_trade_profit NUMERIC(78, 0),
    worst_trade_loss NUMERIC(78, 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_metrics_timestamp ON performance_metrics(timestamp DESC);

CREATE TABLE IF NOT EXISTS ml_training_data (
    id SERIAL PRIMARY KEY,
    features JSONB NOT NULL,
    label NUMERIC(5, 4) NOT NULL,
    actual_profit NUMERIC(78, 0),
    prediction NUMERIC(5, 4),
    timestamp TIMESTAMP NOT NULL,
    used_for_training BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ml_training_timestamp ON ml_training_data(timestamp DESC);
CREATE INDEX idx_ml_training_used ON ml_training_data(used_for_training);

CREATE TABLE IF NOT EXISTS gas_prices (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    base_fee NUMERIC(78, 0) NOT NULL,
    priority_fee NUMERIC(78, 0) NOT NULL,
    max_fee NUMERIC(78, 0) NOT NULL,
    block_number BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_gas_timestamp ON gas_prices(timestamp DESC);

CREATE TABLE IF NOT EXISTS token_prices (
    id SERIAL PRIMARY KEY,
    token_address VARCHAR(42) NOT NULL,
    symbol VARCHAR(20),
    price_usd NUMERIC(20, 8) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_token_prices_address ON token_prices(token_address, timestamp DESC);

CREATE OR REPLACE VIEW daily_performance AS
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as total_trades,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_trades,
    SUM(profit_wei) as total_profit_wei,
    SUM(profit_usd) as total_profit_usd,
    AVG(confidence) as avg_confidence,
    MAX(profit_wei) as best_trade,
    MIN(profit_wei) as worst_trade
FROM trades
GROUP BY DATE(timestamp)
ORDER BY date DESC;

CREATE OR REPLACE VIEW hourly_opportunities AS
SELECT 
    DATE_TRUNC('hour', discovered_at) as hour,
    COUNT(*) as opportunities_found,
    SUM(CASE WHEN executed THEN 1 ELSE 0 END) as opportunities_executed,
    AVG(expected_profit) as avg_expected_profit,
    MAX(expected_profit) as max_expected_profit
FROM opportunities
GROUP BY DATE_TRUNC('hour', discovered_at)
ORDER BY hour DESC;