import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from typing import Dict, List, Tuple, Optional
from collections import deque
import random
from dataclasses import dataclass

@dataclass
class Experience:
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool

class DQNNetwork(nn.Module):
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256):
        super(DQNNetwork, self).__init__()
        self.fc1 = nn.Linear(state_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, hidden_dim)
        self.fc4 = nn.Linear(hidden_dim, action_dim)
        self.dropout = nn.Dropout(0.2)
        
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)
        x = torch.relu(self.fc2(x))
        x = self.dropout(x)
        x = torch.relu(self.fc3(x))
        x = self.fc4(x)
        return x

class TD3Agent:
    def __init__(self, state_dim: int, action_dim: int, lr: float = 1e-4):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.actor = self._build_actor().to(self.device)
        self.critic1 = self._build_critic().to(self.device)
        self.critic2 = self._build_critic().to(self.device)
        
        self.target_actor = self._build_actor().to(self.device)
        self.target_critic1 = self._build_critic().to(self.device)
        self.target_critic2 = self._build_critic().to(self.device)
        
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=lr)
        self.critic1_optimizer = optim.Adam(self.critic1.parameters(), lr=lr)
        self.critic2_optimizer = optim.Adam(self.critic2.parameters(), lr=lr)
        
        self.tau = 0.005
        self.gamma = 0.99
        self.noise_std = 0.2
        self.noise_clip = 0.5
        self.policy_delay = 2
        self.total_steps = 0
        
        self._hard_update(self.target_actor, self.actor)
        self._hard_update(self.target_critic1, self.critic1)
        self._hard_update(self.target_critic2, self.critic2)
        
    def _build_actor(self):
        return nn.Sequential(
            nn.Linear(self.state_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.Linear(256, self.action_dim),
            nn.Tanh()
        )
    
    def _build_critic(self):
        return nn.Sequential(
            nn.Linear(self.state_dim + self.action_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.Linear(256, 1)
        )
    
    def select_action(self, state: np.ndarray, add_noise: bool = True) -> np.ndarray:
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            action = self.actor(state_tensor).cpu().numpy().flatten()
        
        if add_noise:
            noise = np.random.normal(0, self.noise_std, size=action.shape)
            action = action + noise
            action = np.clip(action, -1, 1)
        
        return action
    
    def train(self, replay_buffer, batch_size: int = 256):
        if len(replay_buffer) < batch_size:
            return
        
        batch = random.sample(replay_buffer, batch_size)
        
        states = torch.FloatTensor([e.state for e in batch]).to(self.device)
        actions = torch.FloatTensor([e.action for e in batch]).to(self.device)
        rewards = torch.FloatTensor([e.reward for e in batch]).unsqueeze(1).to(self.device)
        next_states = torch.FloatTensor([e.next_state for e in batch]).to(self.device)
        dones = torch.FloatTensor([e.done for e in batch]).unsqueeze(1).to(self.device)
        
        with torch.no_grad():
            noise = torch.randn_like(actions) * self.noise_std
            noise = torch.clamp(noise, -self.noise_clip, self.noise_clip)
            next_actions = torch.clamp(self.target_actor(next_states) + noise, -1, 1)
            
            target_q1 = self.target_critic1(torch.cat([next_states, next_actions], dim=1))
            target_q2 = self.target_critic2(torch.cat([next_states, next_actions], dim=1))
            target_q = torch.min(target_q1, target_q2)
            target_q = rewards + (1 - dones) * self.gamma * target_q
        
        current_q1 = self.critic1(torch.cat([states, actions], dim=1))
        current_q2 = self.critic2(torch.cat([states, actions], dim=1))
        
        critic1_loss = nn.MSELoss()(current_q1, target_q)
        critic2_loss = nn.MSELoss()(current_q2, target_q)
        
        self.critic1_optimizer.zero_grad()
        critic1_loss.backward()
        self.critic1_optimizer.step()
        
        self.critic2_optimizer.zero_grad()
        critic2_loss.backward()
        self.critic2_optimizer.step()
        
        if self.total_steps % self.policy_delay == 0:
            actor_loss = -self.critic1(torch.cat([states, self.actor(states)], dim=1)).mean()
            
            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            self.actor_optimizer.step()
            
            self._soft_update(self.target_actor, self.actor)
            self._soft_update(self.target_critic1, self.critic1)
            self._soft_update(self.target_critic2, self.critic2)
        
        self.total_steps += 1
    
    def _soft_update(self, target_net, source_net):
        for target_param, param in zip(target_net.parameters(), source_net.parameters()):
            target_param.data.copy_(self.tau * param.data + (1.0 - self.tau) * target_param.data)
    
    def _hard_update(self, target_net, source_net):
        for target_param, param in zip(target_net.parameters(), source_net.parameters()):
            target_param.data.copy_(param.data)

class TradingRLAgent:
    def __init__(self, config: Dict):
        self.config = config
        self.state_dim = config.get('state_dim', 158)
        self.action_dim = config.get('action_dim', 4)
        
        self.agent = TD3Agent(self.state_dim, self.action_dim)
        self.replay_buffer = deque(maxlen=100000)
        
        self.current_state = None
        self.previous_portfolio_value = 1000000
        self.episode_rewards = []
        self.step_count = 0
        
    def get_state_from_market_data(self, market_data: Dict) -> np.ndarray:
        features = []
        
        for symbol in ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']:
            if symbol in market_data:
                data = market_data[symbol]
                features.extend([
                    data.get('price', 0),
                    data.get('volume', 0),
                    data.get('bid', 0),
                    data.get('ask', 0),
                    data.get('spread', 0),
                    data.get('volatility', 0)
                ])
            else:
                features.extend([0] * 6)
        
        portfolio_data = market_data.get('portfolio', {})
        features.extend([
            portfolio_data.get('total_value', 0),
            portfolio_data.get('available_balance', 0),
            portfolio_data.get('num_positions', 0),
            portfolio_data.get('unrealized_pnl', 0)
        ])
        
        while len(features) < self.state_dim:
            features.append(0)
        
        return np.array(features[:self.state_dim], dtype=np.float32)
    
    def select_action(self, market_data: Dict) -> Dict[str, float]:
        state = self.get_state_from_market_data(market_data)
        action_values = self.agent.select_action(state)
        
        actions = {
            'position_size': np.clip(action_values[0], -1, 1),
            'strategy_selection': np.clip(action_values[1], 0, 1),
            'risk_adjustment': np.clip(action_values[2], 0, 1),
            'execution_timing': np.clip(action_values[3], 0, 1)
        }
        
        self.current_state = state
        return actions
    
    def update_reward(self, portfolio_value: float, trade_executed: bool, profit: float):
        reward = 0
        
        portfolio_return = (portfolio_value - self.previous_portfolio_value) / self.previous_portfolio_value
        reward += portfolio_return * 1000
        
        if trade_executed:
            if profit > 0:
                reward += min(profit * 10, 100)
            else:
                reward += max(profit * 5, -50)
        
        reward -= 0.1
        
        self.episode_rewards.append(reward)
        self.previous_portfolio_value = portfolio_value
        
        return reward
    
    def store_experience(self, next_market_data: Dict, reward: float, done: bool = False):
        if self.current_state is not None:
            next_state = self.get_state_from_market_data(next_market_data)
            
            experience = Experience(
                state=self.current_state,
                action=0,
                reward=reward,
                next_state=next_state,
                done=done
            )
            
            self.replay_buffer.append(experience)
    
    def train_agent(self):
        if len(self.replay_buffer) > 1000:
            self.agent.train(self.replay_buffer)
    
    def get_performance_metrics(self) -> Dict:
        if not self.episode_rewards:
            return {}
        
        rewards_array = np.array(self.episode_rewards[-1000:])
        
        return {
            'avg_reward': np.mean(rewards_array),
            'reward_std': np.std(rewards_array),
            'max_reward': np.max(rewards_array),
            'min_reward': np.min(rewards_array),
            'total_episodes': len(self.episode_rewards),
            'replay_buffer_size': len(self.replay_buffer)
        }
    
    def save_model(self, filepath: str):
        torch.save({
            'actor_state_dict': self.agent.actor.state_dict(),
            'critic1_state_dict': self.agent.critic1.state_dict(),
            'critic2_state_dict': self.agent.critic2.state_dict(),
            'episode_rewards': self.episode_rewards,
            'step_count': self.step_count
        }, filepath)
    
    def load_model(self, filepath: str):
        checkpoint = torch.load(filepath)
        self.agent.actor.load_state_dict(checkpoint['actor_state_dict'])
        self.agent.critic1.load_state_dict(checkpoint['critic1_state_dict'])
        self.agent.critic2.load_state_dict(checkpoint['critic2_state_dict'])
        self.episode_rewards = checkpoint.get('episode_rewards', [])
        self.step_count = checkpoint.get('step_count', 0)
