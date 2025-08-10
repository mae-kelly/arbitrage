import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple
import coremltools as ct

class M1OptimizedArbitrageNet(nn.Module):
    def __init__(self, input_dim: int = 128, hidden_dim: int = 512, output_dim: int = 3):
        super().__init__()
        self.input_norm = nn.LayerNorm(input_dim)
        
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim * 2, hidden_dim * 4),
            nn.ReLU(),
        )
        
        self.attention = nn.MultiheadAttention(hidden_dim * 4, num_heads=8)
        
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim * 4, hidden_dim * 2),
            nn.ReLU(),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )
        
        self.value_head = nn.Linear(output_dim, 1)
        self.action_head = nn.Linear(output_dim, 3)
        
    def forward(self, x: torch.Tensor, hidden: torch.Tensor = None) -> Tuple[torch.Tensor, torch.Tensor]:
        x = self.input_norm(x)
        encoded = self.encoder(x)
        
        if hidden is not None:
            attended, _ = self.attention(encoded.unsqueeze(0), hidden.unsqueeze(0), hidden.unsqueeze(0))
            attended = attended.squeeze(0)
        else:
            attended = encoded
            
        decoded = self.decoder(attended)
        
        value = self.value_head(decoded)
        action_logits = self.action_head(decoded)
        
        return F.softmax(action_logits, dim=-1), value

class ReinforcementLearningAgent:
    def __init__(self, state_dim: int = 128, action_dim: int = 3):
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        self.model = M1OptimizedArbitrageNet(state_dim, 512, action_dim).to(self.device)
        self.target_model = M1OptimizedArbitrageNet(state_dim, 512, action_dim).to(self.device)
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=3e-4)
        
        self.memory = []
        self.gamma = 0.99
        self.tau = 0.005
        
    def act(self, state: np.ndarray, epsilon: float = 0.0) -> int:
        if np.random.random() < epsilon:
            return np.random.randint(0, 3)
            
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            action_probs, _ = self.model(state_tensor)
        return torch.multinomial(action_probs, 1).item()
        
    def remember(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool):
        self.memory.append((state, action, reward, next_state, done))
        if len(self.memory) > 100000:
            self.memory.pop(0)
            
    def replay(self, batch_size: int = 256):
        if len(self.memory) < batch_size:
            return
            
        batch = np.random.choice(len(self.memory), batch_size, replace=False)
        states = torch.FloatTensor([self.memory[i][0] for i in batch]).to(self.device)
        actions = torch.LongTensor([self.memory[i][1] for i in batch]).to(self.device)
        rewards = torch.FloatTensor([self.memory[i][2] for i in batch]).to(self.device)
        next_states = torch.FloatTensor([self.memory[i][3] for i in batch]).to(self.device)
        dones = torch.FloatTensor([self.memory[i][4] for i in batch]).to(self.device)
        
        current_action_probs, current_values = self.model(states)
        next_action_probs, next_values = self.target_model(next_states)
        
        target_values = rewards + self.gamma * next_values.squeeze() * (1 - dones)
        
        value_loss = F.mse_loss(current_values.squeeze(), target_values.detach())
        
        action_log_probs = torch.log(current_action_probs.gather(1, actions.unsqueeze(1)))
        advantages = (target_values - current_values.squeeze()).detach()
        policy_loss = -(action_log_probs.squeeze() * advantages).mean()
        
        total_loss = value_loss + policy_loss
        
        self.optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        self.optimizer.step()
        
        self.soft_update()
        
    def soft_update(self):
        for target_param, param in zip(self.target_model.parameters(), self.model.parameters()):
            target_param.data.copy_(self.tau * param.data + (1.0 - self.tau) * target_param.data)

    def export_to_coreml(self, path: str = "arbitrage_model.mlmodel"):
        self.model.eval()
        example_input = torch.randn(1, 128)
        traced_model = torch.jit.trace(self.model, (example_input,))
        
        ml_model = ct.convert(
            traced_model,
            inputs=[ct.TensorType(name="input", shape=(1, 128))],
            outputs=[ct.TensorType(name="action_probs"), ct.TensorType(name="value")],
            compute_units=ct.ComputeUnit.ALL,
            minimum_deployment_target=ct.target.macOS13,
        )
        ml_model.save(path)
