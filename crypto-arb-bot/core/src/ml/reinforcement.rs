use anyhow::Result;
use std::collections::VecDeque;
use parking_lot::RwLock;
use std::sync::Arc;
use ndarray::{Array1, Array2};
use rand::{thread_rng, Rng};

pub struct ReinforcementAgent {
    q_table: Arc<RwLock<HashMap<String, Array1<f64>>>>,
    experience_buffer: Arc<RwLock<VecDeque<Experience>>>,
    epsilon: Arc<RwLock<f64>>,
    learning_rate: f64,
    gamma: f64,
}

use std::collections::HashMap;

#[derive(Clone, Debug)]
struct Experience {
    state: String,
    action: usize,
    reward: f64,
    next_state: String,
    done: bool,
}

impl ReinforcementAgent {
    pub fn new() -> Result<Self> {
        Ok(Self {
            q_table: Arc::new(RwLock::new(HashMap::new())),
            experience_buffer: Arc::new(RwLock::new(VecDeque::with_capacity(100000))),
            epsilon: Arc::new(RwLock::new(1.0)),
            learning_rate: 0.001,
            gamma: 0.99,
        })
    }
    
    pub fn score_opportunity(&self, opp: &crate::Opportunity) -> Result<f64> {
        let state_key = self.encode_state(opp);
        let q_table = self.q_table.read();
        
        if let Some(q_values) = q_table.get(&state_key) {
            Ok(q_values.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b)))
        } else {
            let expected_return = opp.expected_profit.as_u128() as f64 / 1e18;
            let confidence_factor = opp.confidence as f64;
            Ok(expected_return * confidence_factor)
        }
    }
    
    fn encode_state(&self, opp: &crate::Opportunity) -> String {
        format!("{}-{}-{}", opp.chain_a, opp.chain_b, opp.token_a)
    }
    
    pub fn act(&self, state: &str) -> usize {
        let epsilon = *self.epsilon.read();
        let mut rng = thread_rng();
        
        if rng.gen::<f64>() < epsilon {
            rng.gen_range(0..3)
        } else {
            let q_table = self.q_table.read();
            if let Some(q_values) = q_table.get(state) {
                q_values.iter()
                    .enumerate()
                    .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap())
                    .map(|(idx, _)| idx)
                    .unwrap_or(0)
            } else {
                0
            }
        }
    }
    
    pub fn remember(&self, state: String, action: usize, reward: f64, next_state: String, done: bool) {
        let mut buffer = self.experience_buffer.write();
        buffer.push_back(Experience {
            state,
            action,
            reward,
            next_state,
            done,
        });
        
        if buffer.len() > 100000 {
            buffer.pop_front();
        }
    }
    
    pub async fn update(&mut self) -> Result<()> {
        let buffer = self.experience_buffer.read();
        if buffer.len() < 1000 {
            return Ok(());
        }
        
        let mut q_table = self.q_table.write();
        
        for exp in buffer.iter().take(256) {
            let current_q = q_table.entry(exp.state.clone())
                .or_insert_with(|| Array1::zeros(3));
            
            let next_q = q_table.get(&exp.next_state)
                .map(|q| q.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b)))
                .unwrap_or(0.0);
            
            let target = if exp.done {
                exp.reward
            } else {
                exp.reward + self.gamma * next_q
            };
            
            current_q[exp.action] += self.learning_rate * (target - current_q[exp.action]);
        }
        
        let mut epsilon = self.epsilon.write();
        *epsilon = (*epsilon * 0.995).max(0.01);
        
        Ok(())
    }
}
