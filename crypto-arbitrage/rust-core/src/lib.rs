use pyo3::prelude::*;

pub mod types;
pub mod orderbook;
pub mod execution;

#[pymodule]
fn crypto_arbitrage_core(_py: Python, m: &PyModule) -> PyResult<()> {
    Ok(())
}
