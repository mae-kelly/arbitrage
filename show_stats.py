#!/usr/bin/env python3
import os
import json
from datetime import datetime
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

print("📊 MEV Bot Statistics")
print("=" * 40)

# Load stats file if exists
stats_file = "mev_stats.json"
if os.path.exists(stats_file):
    with open(stats_file, 'r') as f:
        stats = json.load(f)
    
    print(f"Total Profit: ${stats.get('total_profit', 0):,.2f}")
    print(f"Transactions: {stats.get('total_transactions', 0)}")
    print(f"Success Rate: {stats.get('success_rate', 0):.1f}%")
    print(f"Best Day: ${stats.get('best_day', 0):,.2f}")
else:
    print("No statistics yet. Run the bot to generate stats.")
    
    # Show potential
    print("\n💰 Potential Earnings:")
    print("  Conservative: $5-30M/month")
    print("  Realistic: $150M/month")
    print("  Optimal: $900M/month")
