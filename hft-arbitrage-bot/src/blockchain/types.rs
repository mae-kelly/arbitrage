// src/blockchain/types.rs
// Common blockchain types that work without full ethers dependency

use serde::{Deserialize, Serialize};

// Re-export common types
pub type Result<T> = anyhow::Result<T>;

// Simple implementations for compilation without ethers
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct U256(pub u64);

impl U256 {
    pub fn zero() -> Self {
        U256(0)
    }
    
    pub fn from(value: u64) -> Self {
        U256(value)
    }
    
    pub fn pow(self, exp: Self) -> Self {
        U256(self.0.pow(exp.0 as u32))
    }
}

impl std::ops::Mul for U256 {
    type Output = Self;
    fn mul(self, rhs: Self) -> Self {
        U256(self.0 * rhs.0)
    }
}

impl std::ops::Div for U256 {
    type Output = Self;
    fn div(self, rhs: Self) -> Self {
        U256(self.0 / rhs.0)
    }
}

impl std::ops::Add for U256 {
    type Output = Self;
    fn add(self, rhs: Self) -> Self {
        U256(self.0 + rhs.0)
    }
}

impl std::ops::Sub for U256 {
    type Output = Self;
    fn sub(self, rhs: Self) -> Self {
        U256(self.0 - rhs.0)
    }
}

impl PartialOrd for U256 {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        self.0.partial_cmp(&other.0)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct H256(pub [u8; 32]);

impl H256 {
    pub fn random() -> Self {
        use rand::Rng;
        let mut rng = rand::thread_rng();
        let mut bytes = [0u8; 32];
        rng.fill(&mut bytes);
        H256(bytes)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Address(pub [u8; 20]);

// Mock provider types for compilation
#[derive(Debug, Clone)]
pub struct Provider<T> {
    _phantom: std::marker::PhantomData<T>,
}

#[derive(Debug, Clone)]
pub struct Ws;

impl<T> Provider<T> {
    pub async fn connect(_url: &str) -> Result<Self> {
        Ok(Provider {
            _phantom: std::marker::PhantomData,
        })
    }
    
    pub async fn request<P, R>(&self, _method: &str, _params: P) -> Result<R> 
    where 
        P: Serialize,
        R: for<'de> Deserialize<'de> + Default,
    {
        Ok(R::default())
    }
}

#[derive(Debug, Clone)]
pub struct SignerMiddleware<P, S> {
    _phantom: std::marker::PhantomData<(P, S)>,
}

impl<P, S> SignerMiddleware<P, S> {
    pub fn new(_provider: P, _signer: S) -> Self {
        SignerMiddleware {
            _phantom: std::marker::PhantomData,
        }
    }
}

#[derive(Debug, Clone)]
pub struct TypedTransaction {
    pub value: Option<U256>,
    pub gas_limit: Option<U256>,
}

impl TypedTransaction {
    pub fn value(&self) -> Option<&U256> {
        self.value.as_ref()
    }
    
    pub fn gas_limit(&self) -> Option<&U256> {
        self.gas_limit.as_ref()
    }
}

// Mock contract types
#[derive(Debug, Clone)]
pub struct ArbitrageContract<M> {
    _phantom: std::marker::PhantomData<M>,
}

impl<M> ArbitrageContract<M> {
    pub fn new(_address: Address, _client: std::sync::Arc<M>) -> Self {
        ArbitrageContract {
            _phantom: std::marker::PhantomData,
        }
    }
}

#[derive(Debug, Clone)]
pub struct IAaveFlashLoan<M> {
    _phantom: std::marker::PhantomData<M>,
}

impl<M> IAaveFlashLoan<M> {
    pub fn new(_address: Address, _client: std::sync::Arc<M>) -> Self {
        IAaveFlashLoan {
            _phantom: std::marker::PhantomData,
        }
    }
}

#[derive(Debug, Clone)]
pub struct IERC20<M> {
    _phantom: std::marker::PhantomData<M>,
}

impl<M> IERC20<M> {
    pub fn new(_address: Address, _client: std::sync::Arc<M>) -> Self {
        IERC20 {
            _phantom: std::marker::PhantomData,
        }
    }
}

#[derive(Debug, Clone)]
pub struct IUniswapV3Pool<M> {
    _phantom: std::marker::PhantomData<M>,
}

impl<M> IUniswapV3Pool<M> {
    pub fn new(_address: Address, _client: std::sync::Arc<M>) -> Self {
        IUniswapV3Pool {
            _phantom: std::marker::PhantomData,
        }
    }
}

// Default implementations for mock types
impl Default for U256 {
    fn default() -> Self {
        U256::zero()
    }
}

impl Default for H256 {
    fn default() -> Self {
        H256([0u8; 32])
    }
}

impl Default for Address {
    fn default() -> Self {
        Address([0u8; 20])
    }
}