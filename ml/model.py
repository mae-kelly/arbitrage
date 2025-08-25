import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import mps
import pickle
import os

class ArbitrageModel(nn.Module):
    def __init__(self):
        super(ArbitrageModel, self).__init__()
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        
        self.fc1 = nn.Linear(10, 256)
        self.bn1 = nn.BatchNorm1d(256)
        self.dropout1 = nn.Dropout(0.3)
        
        self.fc2 = nn.Linear(256, 512)
        self.bn2 = nn.BatchNorm1d(512)
        self.dropout2 = nn.Dropout(0.3)
        
        self.fc3 = nn.Linear(512, 1024)
        self.bn3 = nn.BatchNorm1d(1024)
        self.dropout3 = nn.Dropout(0.3)
        
        self.fc4 = nn.Linear(1024, 512)
        self.bn4 = nn.BatchNorm1d(512)
        self.dropout4 = nn.Dropout(0.3)
        
        self.fc5 = nn.Linear(512, 256)
        self.bn5 = nn.BatchNorm1d(256)
        self.dropout5 = nn.Dropout(0.3)
        
        self.fc6 = nn.Linear(256, 128)
        self.bn6 = nn.BatchNorm1d(128)
        
        self.fc7 = nn.Linear(128, 64)
        self.bn7 = nn.BatchNorm1d(64)
        
        self.fc8 = nn.Linear(64, 32)
        self.bn8 = nn.BatchNorm1d(32)
        
        self.fc9 = nn.Linear(32, 16)
        self.fc10 = nn.Linear(16, 1)
        
        self.attention = nn.MultiheadAttention(256, 8, batch_first=True)
        self.lstm = nn.LSTM(256, 128, 2, batch_first=True, bidirectional=True)
        self.gru = nn.GRU(256, 128, 2, batch_first=True)
        
        self.to(self.device)
        
    def forward(self, x):
        x = x.to(self.device)
        
        x = F.relu(self.bn1(self.fc1(x)))
        x = self.dropout1(x)
        
        residual = x
        x = F.relu(self.bn2(self.fc2(x)))
        x = self.dropout2(x)
        
        x = F.relu(self.bn3(self.fc3(x)))
        x = self.dropout3(x)
        
        x = F.relu(self.bn4(self.fc4(x)))
        x = self.dropout4(x)
        
        x = F.relu(self.bn5(self.fc5(x)))
        x = self.dropout5(x) + residual
        
        if x.dim() == 2:
            x = x.unsqueeze(1)
        
        attn_out, _ = self.attention(x, x, x)
        x = x + attn_out
        
        lstm_out, _ = self.lstm(x)
        gru_out, _ = self.gru(x)
        
        x = lstm_out + gru_out
        
        if x.dim() == 3:
            x = x.squeeze(1)
        
        x = F.relu(self.bn6(self.fc6(x[:, :256])))
        x = F.relu(self.bn7(self.fc7(x)))
        x = F.relu(self.bn8(self.fc8(x)))
        x = F.relu(self.fc9(x))
        x = torch.sigmoid(self.fc10(x))
        
        return x
    
    def predict(self, features):
        self.eval()
        with torch.no_grad():
            if isinstance(features, list):
                features = np.array(features, dtype=np.float32)
            if len(features.shape) == 1:
                features = features.reshape(1, -1)
            
            x = torch.from_numpy(features).float()
            output = self.forward(x)
            
            return output.cpu().numpy()[0][0]
    
    def backward_pass(self, x, y, learning_rate=0.001):
        self.train()
        optimizer = torch.optim.AdamW(self.parameters(), lr=learning_rate)
        criterion = nn.MSELoss()
        
        x = torch.from_numpy(np.array(x, dtype=np.float32)).to(self.device)
        y = torch.from_numpy(np.array(y, dtype=np.float32)).to(self.device)
        
        optimizer.zero_grad()
        output = self.forward(x)
        loss = criterion(output, y)
        loss.backward()
        optimizer.step()
        
        return loss.item()
    
    def load_weights(self):
        try:
            if os.path.exists('ml/weights.pth'):
                self.load_state_dict(torch.load('ml/weights.pth', map_location=self.device))
            else:
                self.initialize_weights()
        except:
            self.initialize_weights()
    
    def save_weights(self):
        torch.save(self.state_dict(), 'ml/weights.pth')
    
    def initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
            elif isinstance(m, (nn.LSTM, nn.GRU)):
                for param in m.parameters():
                    if len(param.shape) >= 2:
                        nn.init.orthogonal_(param)
                    else:
                        nn.init.zeros_(param)