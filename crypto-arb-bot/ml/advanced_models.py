import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn import TransformerEncoder, TransformerEncoderLayer
import numpy as np
from typing import Dict, List, Tuple, Optional
import coremltools as ct
from dataclasses import dataclass

@dataclass
class MarketState:
    prices: torch.Tensor
    volumes: torch.Tensor
    order_books: torch.Tensor
    mempool: torch.Tensor
    sentiment: torch.Tensor
    
class TransformerArbitrageNet(nn.Module):
    def __init__(
        self,
        input_dim: int = 512,
        d_model: int = 256,
        nhead: int = 8,
        num_layers: int = 6,
        dim_feedforward: int = 1024,
        dropout: float = 0.1
    ):
        super().__init__()
        
        self.input_projection = nn.Linear(input_dim, d_model)
        self.positional_encoding = PositionalEncoding(d_model, dropout)
        
        encoder_layers = TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            activation='gelu',
            batch_first=True
        )
        self.transformer = TransformerEncoder(encoder_layers, num_layers)
        
        self.lstm = nn.LSTM(
            d_model,
            d_model // 2,
            num_layers=3,
            batch_first=True,
            dropout=dropout,
            bidirectional=True
        )
        
        self.attention_pool = nn.MultiheadAttention(d_model, nhead, batch_first=True)
        
        self.output_layers = nn.Sequential(
            nn.Linear(d_model, d_model * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model * 2, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        
        self.action_head = nn.Linear(d_model, 5)
        self.value_head = nn.Linear(d_model, 1)
        self.confidence_head = nn.Linear(d_model, 1)
        
    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        
        x = self.input_projection(x)
        x = self.positional_encoding(x)
        
        transformer_out = self.transformer(x, mask)
        
        lstm_out, (hidden, cell) = self.lstm(transformer_out)
        
        query = transformer_out.mean(dim=1, keepdim=True)
        attended, _ = self.attention_pool(query, lstm_out, lstm_out)
        attended = attended.squeeze(1)
        
        features = self.output_layers(attended)
        
        actions = F.softmax(self.action_head(features), dim=-1)
        values = self.value_head(features)
        confidence = torch.sigmoid(self.confidence_head(features))
        
        return actions, values, confidence

class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 5000):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-np.log(10000.0) / d_model))
        pe = torch.zeros(max_len, d_model)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:x.size(1)]
        return self.dropout(x)

class MemPoolPredictor(nn.Module):
    def __init__(self, input_dim: int = 256, hidden_dim: int = 512):
        super().__init__()
        
        self.conv1d_layers = nn.Sequential(
            nn.Conv1d(input_dim, hidden_dim, kernel_size=3, padding=1),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Conv1d(hidden_dim, hidden_dim, kernel_size=3, padding=1),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Conv1d(hidden_dim, hidden_dim // 2, kernel_size=3, padding=1),
            nn.BatchNorm1d(hidden_dim // 2),
            nn.ReLU(),
        )
        
        self.gru = nn.GRU(
            hidden_dim // 2,
            hidden_dim // 4,
            num_layers=2,
            batch_first=True,
            dropout=0.1,
            bidirectional=True
        )
        
        self.output = nn.Sequential(
            nn.Linear(hidden_dim // 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, 3)
        )
        
    def forward(self, mempool_data: torch.Tensor) -> torch.Tensor:
        x = mempool_data.transpose(1, 2)
        x = self.conv1d_layers(x)
        x = x.transpose(1, 2)
        
        x, _ = self.gru(x)
        x = x[:, -1, :]
        
        return self.output(x)

class DeepQLearningAgent:
    def __init__(self, state_dim: int = 512, action_dim: int = 5):
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        
        self.online_net = TransformerArbitrageNet(state_dim).to(self.device)
        self.target_net = TransformerArbitrageNet(state_dim).to(self.device)
        self.mempool_predictor = MemPoolPredictor().to(self.device)
        
        self.optimizer = torch.optim.AdamW(
            list(self.online_net.parameters()) + list(self.mempool_predictor.parameters()),
            lr=1e-4,
            weight_decay=1e-5
        )
        
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
            self.optimizer,
            T_0=1000,
            T_mult=2
        )
        
        self.memory = PrioritizedReplayBuffer(capacity=1000000)
        self.steps = 0
        self.tau = 0.001
        
    def act(self, state: MarketState, epsilon: float = 0.0) -> Tuple[int, float]:
        if np.random.random() < epsilon:
            return np.random.randint(0, 5), 0.0
            
        with torch.no_grad():
            state_tensor = self.encode_state(state).to(self.device)
            actions, values, confidence = self.online_net(state_tensor)
            
            mempool_pred = self.mempool_predictor(state.mempool)
            
            adjusted_actions = actions * (1 + mempool_pred.softmax(dim=-1))
            
            action = torch.multinomial(adjusted_actions.squeeze(), 1).item()
            conf = confidence.item()
            
        return action, conf
    
    def encode_state(self, state: MarketState) -> torch.Tensor:
        features = []
        
        features.append(state.prices.flatten())
        features.append(state.volumes.flatten())
        features.append(state.order_books.flatten())
        
        mempool_features = self.mempool_predictor(state.mempool)
        features.append(mempool_features.flatten())
        
        features.append(state.sentiment.flatten())
        
        return torch.cat(features).unsqueeze(0)
    
    def train_step(self, batch_size: int = 128) -> Dict[str, float]:
        if len(self.memory) < batch_size:
            return {}
            
        transitions, weights, indices = self.memory.sample(batch_size)
        
        states = torch.stack([self.encode_state(t.state) for t in transitions]).to(self.device)
        actions = torch.tensor([t.action for t in transitions]).to(self.device)
        rewards = torch.tensor([t.reward for t in transitions]).to(self.device)
        next_states = torch.stack([self.encode_state(t.next_state) for t in transitions]).to(self.device)
        dones = torch.tensor([t.done for t in transitions]).to(self.device)
        weights = torch.tensor(weights).to(self.device)
        
        current_actions, current_values, current_confidence = self.online_net(states)
        
        with torch.no_grad():
            next_actions, next_values, _ = self.target_net(next_states)
            next_q_values = next_values.squeeze() * (1 - dones)
            target_values = rewards + 0.99 * next_q_values
        
        td_errors = (current_values.squeeze() - target_values).abs()
        self.memory.update_priorities(indices, td_errors.cpu().numpy())
        
        value_loss = F.smooth_l1_loss(
            current_values.squeeze(),
            target_values,
            reduction='none'
        )
        value_loss = (value_loss * weights).mean()
        
        action_log_probs = torch.log(current_actions.gather(1, actions.unsqueeze(1)) + 1e-8)
        advantages = (target_values - current_values.squeeze()).detach()
        policy_loss = -(action_log_probs.squeeze() * advantages * weights).mean()
        
        confidence_targets = (td_errors < 0.1).float()
        confidence_loss = F.binary_cross_entropy(
            current_confidence.squeeze(),
            confidence_targets
        )
        
        total_loss = value_loss + 0.5 * policy_loss + 0.1 * confidence_loss
        
        self.optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.online_net.parameters(), 1.0)
        self.optimizer.step()
        self.scheduler.step()
        
        self.soft_update()
        self.steps += 1
        
        return {
            'value_loss': value_loss.item(),
            'policy_loss': policy_loss.item(),
            'confidence_loss': confidence_loss.item(),
            'total_loss': total_loss.item(),
            'learning_rate': self.scheduler.get_last_lr()[0]
        }
    
    def soft_update(self):
        for target_param, param in zip(self.target_net.parameters(), self.online_net.parameters()):
            target_param.data.copy_(self.tau * param.data + (1.0 - self.tau) * target_param.data)

class PrioritizedReplayBuffer:
    def __init__(self, capacity: int, alpha: float = 0.6, beta: float = 0.4):
        self.capacity = capacity
        self.alpha = alpha
        self.beta = beta
        self.buffer = []
        self.priorities = np.zeros(capacity, dtype=np.float32)
        self.position = 0
        
    def push(self, transition):
        max_priority = self.priorities.max() if self.buffer else 1.0
        
        if len(self.buffer) < self.capacity:
            self.buffer.append(transition)
        else:
            self.buffer[self.position] = transition
            
        self.priorities[self.position] = max_priority
        self.position = (self.position + 1) % self.capacity
        
    def sample(self, batch_size: int):
        if len(self.buffer) == self.capacity:
            priorities = self.priorities
        else:
            priorities = self.priorities[:self.position]
            
        probabilities = priorities ** self.alpha
        probabilities /= probabilities.sum()
        
        indices = np.random.choice(len(self.buffer), batch_size, p=probabilities)
        transitions = [self.buffer[idx] for idx in indices]
        
        total = len(self.buffer)
        weights = (total * probabilities[indices]) ** (-self.beta)
        weights /= weights.max()
        
        return transitions, weights, indices
    
    def update_priorities(self, indices, td_errors):
        for idx, td_error in zip(indices, td_errors):
            priority = (abs(td_error) + 1e-6) ** self.alpha
            self.priorities[idx] = priority
    
    def __len__(self):
        return len(self.buffer)

class MetalOptimizedInference:
    def __init__(self, model_path: str):
        self.model = ct.models.MLModel(model_path)
        self.device = torch.device("mps")
        
    def predict_batch(self, inputs: np.ndarray) -> np.ndarray:
        inputs_dict = {"input": inputs}
        predictions = self.model.predict(inputs_dict)
        return predictions["output"]
    
    def optimize_for_m1(self, model: nn.Module):
        model.eval()
        example_input = torch.randn(1, 512).to(self.device)
        
        traced = torch.jit.trace(model, example_input)
        
        ml_model = ct.convert(
            traced,
            inputs=[ct.TensorType(name="input", shape=(1, 512))],
            outputs=[
                ct.TensorType(name="actions"),
                ct.TensorType(name="values"),
                ct.TensorType(name="confidence")
            ],
            compute_units=ct.ComputeUnit.ALL,
            compute_precision=ct.precision.FLOAT16,
            minimum_deployment_target=ct.target.macOS13,
        )
        
        ml_model.save("optimized_arbitrage_model.mlpackage")
        return ml_model
