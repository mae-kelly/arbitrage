import asyncio
import torch
import numpy as np
from advanced_models import DeepQLearningAgent, MarketState
from dataset import RealTimeDataset
import wandb
import time

async def train_advanced():
    wandb.init(project="crypto-arbitrage", name="deep-q-transformer")
    
    agent = DeepQLearningAgent(state_dim=512, action_dim=5)
    dataset = RealTimeDataset()
    
    epsilon = 1.0
    epsilon_decay = 0.995
    epsilon_min = 0.01
    
    best_reward = float('-inf')
    
    for episode in range(100000):
        episode_reward = 0
        prices = await dataset.get_realtime_prices()
        
        state = MarketState(
            prices=torch.randn(100, 10),
            volumes=torch.randn(100, 10),
            order_books=torch.randn(100, 20),
            mempool=torch.randn(100, 256),
            sentiment=torch.randn(100, 5)
        )
        
        for step in range(1000):
            action, confidence = agent.act(state, epsilon)
            
            await asyncio.sleep(0.001)
            
            next_prices = await dataset.get_realtime_prices()
            next_state = MarketState(
                prices=torch.randn(100, 10),
                volumes=torch.randn(100, 10),
                order_books=torch.randn(100, 20),
                mempool=torch.randn(100, 256),
                sentiment=torch.randn(100, 5)
            )
            
            reward = calculate_reward(action, state, next_state)
            episode_reward += reward
            
            agent.memory.push(Transition(state, action, reward, next_state, False))
            
            if len(agent.memory) > 1000:
                metrics = agent.train_step(batch_size=256)
                wandb.log(metrics)
            
            state = next_state
            
            if step % 100 == 0:
                print(f"Episode {episode}, Step {step}, Reward: {episode_reward:.2f}")
        
        epsilon = max(epsilon_min, epsilon * epsilon_decay)
        
        if episode_reward > best_reward:
            best_reward = episode_reward
            torch.save(agent.online_net.state_dict(), f"models/best_model_{episode}.pt")
            agent.mempool_predictor.optimize_for_m1(agent.online_net)
        
        wandb.log({
            "episode": episode,
            "reward": episode_reward,
            "epsilon": epsilon,
            "confidence": confidence
        })

def calculate_reward(action, state, next_state):
    price_change = next_state.prices[0, 0] - state.prices[0, 0]
    
    if action == 0:  # Buy
        return price_change.item()
    elif action == 1:  # Sell
        return -price_change.item()
    elif action == 2:  # Hold
        return -0.0001
    else:
        return 0.0

class Transition:
    def __init__(self, state, action, reward, next_state, done):
        self.state = state
        self.action = action
        self.reward = reward
        self.next_state = next_state
        self.done = done

if __name__ == "__main__":
    asyncio.run(train_advanced())
