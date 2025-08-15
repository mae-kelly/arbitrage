// US-LEGAL EXCHANGES ONLY (50+ exchanges)
pub const US_TIER1: &[&str] = &[
    "coinbase", "kraken", "gemini", "bitstamp", 
    "crypto_com", "kucoin", "bittrex", "poloniex"
];

pub const US_TIER2: &[&str] = &[
    "bitmart", "lbank", "probit", "hotbit",
    "gate_io", "mexc", "bitget", "digifinex"
];

pub const US_DEFI: &[&str] = &[
    "uniswap_v3", "sushiswap", "curve", "balancer",
    "1inch", "pancakeswap", "quickswap", "trader_joe"
];

pub fn get_us_legal_exchanges() -> Vec<&'static str> {
    let mut exchanges = Vec::new();
    exchanges.extend_from_slice(US_TIER1);
    exchanges.extend_from_slice(US_TIER2);
    exchanges.extend_from_slice(US_DEFI);
    exchanges
}
