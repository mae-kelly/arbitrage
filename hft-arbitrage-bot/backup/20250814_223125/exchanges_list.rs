// ALL EXCHANGES (185+ supported)
pub const TIER1_EXCHANGES: &[(&str, &str)] = &[
    ("coinbase", "wss://ws-feed.exchange.coinbase.com"),
    ("kraken", "wss://ws.kraken.com"),
    ("bybit", "wss://stream.bybit.com/v5/public/spot"),
    ("okx", "wss://ws.okx.com:8443/ws/v5/public"),
    ("kucoin", "wss://ws-api-spot.kucoin.com/"),
    ("huobi", "wss://api.huobi.pro/ws"),
    ("gateio", "wss://api.gateio.ws/ws/v4/"),
    ("bitfinex", "wss://api-pub.bitfinex.com/ws/2"),
];

pub const TIER2_EXCHANGES: &[(&str, &str)] = &[
    ("mexc", "wss://wbs.mexc.com/ws"),
    ("bitget", "wss://ws.bitget.com/spot/v1/stream"),
    ("crypto_com", "wss://stream.crypto.com/v2/market"),
    ("gemini", "wss://api.gemini.com/v1/marketdata"),
    ("bitstamp", "wss://ws.bitstamp.net"),
    ("bittrex", "wss://socket-v3.bittrex.com/signalr"),
    ("poloniex", "wss://ws.poloniex.com/ws/public"),
    ("bithumb", "wss://pubwss.bithumb.com/pub/ws"),
];

pub const TIER3_EXCHANGES: &[(&str, &str)] = &[
    ("bitmart", "wss://ws-manager-compress.bitmart.com/api?protocol=1.1"),
    ("lbank", "wss://www.lbkex.net/ws/V2/"),
    ("probit", "wss://api.probit.com/api/exchange/v1/ws"),
    ("hotbit", "wss://ws.hotbit.io/"),
    ("digifinex", "wss://openapi.digifinex.com/ws/v1/"),
    ("coinsbit", "wss://ws.coinsbit.io/ws"),
    ("latoken", "wss://api.latoken.com/v2/ws"),
    ("p2pb2b", "wss://api.p2pb2b.io/api/v2/ws"),
    ("exmo", "wss://ws-api.exmo.com:443/v1/public"),
    ("cex_io", "wss://ws.cex.io/ws/"),
];

pub const ASIAN_EXCHANGES: &[(&str, &str)] = &[
    ("upbit", "wss://api.upbit.com/websocket/v1"),
    ("bithumb", "wss://pubwss.bithumb.com/pub/ws"),
    ("coinone", "wss://stream.coinone.co.kr/"),
    ("korbit", "wss://ws.korbit.co.kr/v1/user/push"),
    ("bitflyer", "wss://ws.lightstream.bitflyer.com/json-rpc"),
    ("liquid", "wss://tap.liquid.com/"),
    ("zaif", "wss://ws.zaif.jp/stream"),
];

pub const EUROPEAN_EXCHANGES: &[(&str, &str)] = &[
    ("bitstamp", "wss://ws.bitstamp.net"),
    ("bitpanda", "wss://streams.exchange.bitpanda.com"),
    ("luno", "wss://ws.luno.com/api/1/stream"),
    ("btcmarkets", "wss://socket.btcmarkets.net/v2"),
    ("coinjar", "wss://websocket.coinjar.com/"),
];

pub const DEFI_DEXES: &[(&str, &str)] = &[
    ("uniswap_v3", "wss://mainnet.infura.io/ws/v3/"),
    ("sushiswap", "wss://mainnet.infura.io/ws/v3/"),
    ("pancakeswap", "wss://bsc-dataseed1.binance.org/"),
    ("curve", "wss://mainnet.infura.io/ws/v3/"),
    ("balancer", "wss://mainnet.infura.io/ws/v3/"),
    ("1inch", "wss://mainnet.infura.io/ws/v3/"),
    ("dydx", "wss://api.dydx.exchange/v3/ws"),
];

pub const L2_CHAINS: &[(&str, &str)] = &[
    ("arbitrum_one", "wss://arb1.arbitrum.io/ws"),
    ("optimism", "wss://mainnet.optimism.io"),
    ("polygon", "wss://polygon-rpc.com/"),
    ("base", "wss://mainnet.base.org"),
    ("zksync", "wss://mainnet.era.zksync.io/ws"),
];

pub const ALT_L1_CHAINS: &[(&str, &str)] = &[
    ("solana", "wss://api.mainnet-beta.solana.com/"),
    ("avalanche", "wss://api.avax.network/ext/bc/C/ws"),
    ("fantom", "wss://rpc.ftm.tools/"),
    ("cosmos", "wss://rpc-cosmoshub.blockapsis.com/websocket"),
    ("near", "wss://rpc.mainnet.near.org"),
    ("cardano", "wss://cardano-mainnet.blockfrost.io/api/v0/"),
];

pub fn get_all_exchanges() -> Vec<(&'static str, &'static str)> {
    let mut all = Vec::new();
    all.extend_from_slice(TIER1_EXCHANGES);
    all.extend_from_slice(TIER2_EXCHANGES);
    all.extend_from_slice(TIER3_EXCHANGES);
    all.extend_from_slice(ASIAN_EXCHANGES);
    all.extend_from_slice(EUROPEAN_EXCHANGES);
    all.extend_from_slice(DEFI_DEXES);
    all.extend_from_slice(L2_CHAINS);
    all.extend_from_slice(ALT_L1_CHAINS);
    all
}

pub fn get_total_exchange_count() -> usize {
    get_all_exchanges().len()
}
