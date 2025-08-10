pub struct PriceEngine {
    pub name: String,
}

impl PriceEngine {
    pub fn new() -> Self {
        Self {
            name: "PriceEngine".to_string(),
        }
    }
}
