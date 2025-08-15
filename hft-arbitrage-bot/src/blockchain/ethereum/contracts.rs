//! Smart contract registry and interfaces

use ethers::prelude::*;
use anyhow::Result;
use std::collections::HashMap;

abigen!(
    ArbitrageContract,
    "./contracts/ArbitrageContract.json"
);

abigen!(
    IERC20,
    "./contracts/IERC20.json"
);

abigen!(
    IUniswapV3Pool,
    "./contracts/IUniswapV3Pool.json"
);

abigen!(
    IAaveFlashLoan,
    "./contracts/IAaveFlashLoan.json"
);

pub struct ContractRegistry {
    pub arbitrage_contract: ArbitrageContract<SignerMiddleware<Provider<Ws>, LocalWallet>>,
    pub aave_lending_pool: IAaveFlashLoan<SignerMiddleware<Provider<Ws>, LocalWallet>>,
    pub tokens: HashMap<String, IERC20<SignerMiddleware<Provider<Ws>, LocalWallet>>>,
    pub uniswap_pools: HashMap<String, IUniswapV3Pool<SignerMiddleware<Provider<Ws>, LocalWallet>>>,
}

impl ContractRegistry {
    pub async fn new(signer: Arc<SignerMiddleware<Provider<Ws>, LocalWallet>>) -> Result<Self> {
        // Deploy or connect to arbitrage contract
        let arbitrage_address = "0x...".parse()?; // Replace with actual address
        let arbitrage_contract = ArbitrageContract::new(arbitrage_address, signer.clone());
        
        // Connect to Aave lending pool
        let aave_address = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2".parse()?; // Aave V3
        let aave_lending_pool = IAaveFlashLoan::new(aave_address, signer.clone());
        
        // Initialize token contracts
        let mut tokens = HashMap::new();
        let usdc_address = "0xA0b86a33E6417Ee1C2732FC8e48a8F9F8F0C48D6".parse()?;
        tokens.insert("USDC".to_string(), IERC20::new(usdc_address, signer.clone()));
        
        // Initialize Uniswap pools
        let mut uniswap_pools = HashMap::new();
        let weth_usdc_pool = "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640".parse()?;
        uniswap_pools.insert("WETH-USDC".to_string(), IUniswapV3Pool::new(weth_usdc_pool, signer));
        
        Ok(Self {
            arbitrage_contract,
            aave_lending_pool,
            tokens,
            uniswap_pools,
        })
    }
}
