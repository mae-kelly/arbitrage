// TOP 1000+ CRYPTOCURRENCIES
pub const TOP_COINS: &[&str] = &[
    "BTC", "ETH", "BNB", "ADA", "SOL", "XRP", "DOT", "AVAX",
    "MATIC", "LINK", "UNI", "ATOM", "XLM", "VET", "FIL", "TRX",
    "ETC", "THETA", "ICP", "CAKE", "AAVE", "GRT", "MKR", "COMP",
    "YFI", "SNX", "CRV", "BAL", "SUSHI", "REN", "KNC", "LRC",
    "ZRX", "BAND", "OMG", "ANT", "MLN", "REP", "BAT", "ZIL"
];

pub const DEFI_TOKENS: &[&str] = &[
    "UNI", "SUSHI", "AAVE", "MKR", "COMP", "YFI", "SNX", "CRV",
    "BAL", "1INCH", "ALPHA", "CREAM", "HEGIC", "PICKLE", "RARI"
];

pub const GAMING_NFTS: &[&str] = &[
    "AXS", "SLP", "SAND", "MANA", "ENJ", "ALICE", "TLM", "GALA"
];

pub const MEME_COINS: &[&str] = &[
    "DOGE", "SHIB", "FLOKI", "ELON", "DOGELON", "BABYDOGE"
];

pub fn get_all_supported_coins() -> Vec<String> {
    let mut coins = Vec::new();
    for coin in TOP_COINS { coins.push(coin.to_string()); }
    for coin in DEFI_TOKENS { coins.push(coin.to_string()); }
    for coin in GAMING_NFTS { coins.push(coin.to_string()); }
    for coin in MEME_COINS { coins.push(coin.to_string()); }
    coins
}
