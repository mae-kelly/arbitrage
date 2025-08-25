import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from model import ArbitrageModel
import json
import os
from datetime import datetime

class ArbitrageTrainer:
    def __init__(self):
        self.model = ArbitrageModel()
        self.device = self.model.device
        self.optimizer = optim.AdamW(self.model.parameters(), lr=0.001, weight_decay=1e-5)
        self.scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(self.optimizer, T_0=10, T_mult=2)
        self.criterion = nn.BCELoss()
        self.history = []
        
    def generate_synthetic_data(self, n_samples=10000):
        X = np.random.randn(n_samples, 10).astype(np.float32)
        
        X[:, 0] = np.abs(X[:, 0]) * 1e18
        X[:, 1] = np.abs(X[:, 1]) * 30
        X[:, 2] = np.abs(X[:, 2]) * 1e9
        X[:, 3] = np.abs(X[:, 3]) * 20000000
        X[:, 4] = np.random.choice([1, 2, 3, 4, 5], n_samples)
        X[:, 5] = np.random.choice([1, 2, 3, 4, 5], n_samples)
        X[:, 6] = np.random.randn(n_samples) * 1e10
        X[:, 7] = np.random.randn(n_samples) * 1e10
        X[:, 8] = np.random.randn(n_samples) * 1e16
        X[:, 9] = np.random.uniform(0, 1, n_samples)
        
        profit_signal = (
            (X[:, 4] != X[:, 5]).astype(float) * 0.3 +
            (X[:, 8] > 0).astype(float) * 0.4 +
            np.random.randn(n_samples) * 0.1 +
            (X[:, 9] > 0.5).astype(float) * 0.2
        )
        
        y = (profit_signal > 0.5).astype(np.float32).reshape(-1, 1)
        
        return X, y
    
    def train(self, epochs=100, batch_size=64):
        X_train, y_train = self.generate_synthetic_data(50000)
        X_val, y_val = self.generate_synthetic_data(10000)
        
        train_dataset = TensorDataset(
            torch.from_numpy(X_train).float(),
            torch.from_numpy(y_train).float()
        )
        val_dataset = TensorDataset(
            torch.from_numpy(X_val).float(),
            torch.from_numpy(y_val).float()
        )
        
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        
        best_val_loss = float('inf')
        patience = 20
        patience_counter = 0
        
        for epoch in range(epochs):
            self.model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            
            for batch_x, batch_y in train_loader:
                batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                
                self.optimizer.zero_grad()
                outputs = self.model(batch_x)
                loss = self.criterion(outputs, batch_y)
                
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                self.optimizer.step()
                
                train_loss += loss.item()
                predicted = (outputs > 0.5).float()
                train_correct += (predicted == batch_y).sum().item()
                train_total += batch_y.size(0)
            
            self.scheduler.step()
            
            self.model.eval()
            val_loss = 0.0
            val_correct = 0
            val_total = 0
            
            with torch.no_grad():
                for batch_x, batch_y in val_loader:
                    batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                    outputs = self.model(batch_x)
                    loss = self.criterion(outputs, batch_y)
                    
                    val_loss += loss.item()
                    predicted = (outputs > 0.5).float()
                    val_correct += (predicted == batch_y).sum().item()
                    val_total += batch_y.size(0)
            
            avg_train_loss = train_loss / len(train_loader)
            avg_val_loss = val_loss / len(val_loader)
            train_acc = train_correct / train_total
            val_acc = val_correct / val_total
            
            self.history.append({
                'epoch': epoch,
                'train_loss': avg_train_loss,
                'val_loss': avg_val_loss,
                'train_acc': train_acc,
                'val_acc': val_acc,
                'lr': self.optimizer.param_groups[0]['lr']
            })
            
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                self.model.save_weights()
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch}")
                break
            
            if epoch % 10 == 0:
                print(f"Epoch {epoch}: Train Loss={avg_train_loss:.4f}, Val Loss={avg_val_loss:.4f}, Train Acc={train_acc:.4f}, Val Acc={val_acc:.4f}")
    
    def fine_tune(self, real_data_path=None):
        if real_data_path and os.path.exists(real_data_path):
            with open(real_data_path, 'r') as f:
                data = json.load(f)
            
            X = np.array([d['features'] for d in data], dtype=np.float32)
            y = np.array([d['profitable'] for d in data], dtype=np.float32).reshape(-1, 1)
            
            dataset = TensorDataset(
                torch.from_numpy(X).float(),
                torch.from_numpy(y).float()
            )
            loader = DataLoader(dataset, batch_size=32, shuffle=True)
            
            self.model.train()
            for _ in range(10):
                for batch_x, batch_y in loader:
                    batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                    
                    self.optimizer.zero_grad()
                    outputs = self.model(batch_x)
                    loss = self.criterion(outputs, batch_y)
                    loss.backward()
                    self.optimizer.step()
            
            self.model.save_weights()
    
    def evaluate(self, X_test, y_test):
        self.model.eval()
        with torch.no_grad():
            X_test = torch.from_numpy(X_test).float().to(self.device)
            y_test = torch.from_numpy(y_test).float().to(self.device)
            
            outputs = self.model(X_test)
            loss = self.criterion(outputs, y_test)
            
            predicted = (outputs > 0.5).float()
            accuracy = (predicted == y_test).sum().item() / y_test.size(0)
            
            tp = ((predicted == 1) & (y_test == 1)).sum().item()
            fp = ((predicted == 1) & (y_test == 0)).sum().item()
            fn = ((predicted == 0) & (y_test == 1)).sum().item()
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
        return {
            'loss': loss.item(),
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1
        }

if __name__ == "__main__":
    trainer = ArbitrageTrainer()
    trainer.train(epochs=200, batch_size=128)
    trainer.fine_tune("ml/real_data.json")
    
    X_test, y_test = trainer.generate_synthetic_data(1000)
    metrics = trainer.evaluate(X_test, y_test)
    print(f"Test Metrics: {metrics}")