// Re-export common blockchain types for use throughout the application

#[cfg(feature = "ethereum")]
pub use ethers::types::{Address, H256, U256, Transaction as EthTransaction};

#[cfg(feature = "ethereum")]
pub use ethers::providers::{Provider, Ws, Http, Middleware};

#[cfg(feature = "ethereum")]
pub use ethers::signers::{LocalWallet, Signer};

#[cfg(feature = "ethereum")]
pub use ethers::middleware::SignerMiddleware;

#[cfg(feature = "ethereum")]
pub use ethers::contract::Contract;

// For when ethereum feature is not enabled, provide mock types
#[cfg(not(feature = "ethereum"))]
pub mod mock_types {
    use serde::{Deserialize, Serialize};
    
    #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
    pub struct Address([u8; 20]);
    
    impl Default for Address {
        fn default() -> Self {
            Self([0u8; 20])
        }
    }
    
    #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
    pub struct H256([u8; 32]);
    
    impl H256 {
        pub fn random() -> Self {
            Self([0u8; 32])
        }
    }
    
    impl Default for H256 {
        fn default() -> Self {
            Self([0u8; 32])
        }
    }
    
    #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
    pub struct U256(u64);
    
    impl U256 {
        pub fn from(value: u64) -> Self {
            Self(value)
        }
        
        pub fn zero() -> Self {
            Self(0)
        }
    }
    
    impl Default for U256 {
        fn default() -> Self {
            Self(0)
        }
    }
    
    impl std::ops::Add for U256 {
        type Output = Self;
        fn add(self, other: Self) -> Self {
            Self(self.0 + other.0)
        }
    }
    
    impl std::ops::Sub for U256 {
        type Output = Self;
        fn sub(self, other: Self) -> Self {
            Self(self.0 - other.0)
        }
    }
    
    impl std::ops::Mul for U256 {
        type Output = Self;
        fn mul(self, other: Self) -> Self {
            Self(self.0 * other.0)
        }
    }
    
    impl std::ops::Div for U256 {
        type Output = Self;
        fn div(self, other: Self) -> Self {
            Self(self.0 / other.0)
        }
    }
}

#[cfg(not(feature = "ethereum"))]
pub use mock_types::*;

// Common result type
pub type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;

// Mock provider types when ethereum feature is disabled
#[cfg(not(feature = "ethereum"))]
pub struct Provider<T>(std::marker::PhantomData<T>);

#[cfg(not(feature = "ethereum"))]
pub struct Ws;

#[cfg(not(feature = "ethereum"))]
pub struct Http;