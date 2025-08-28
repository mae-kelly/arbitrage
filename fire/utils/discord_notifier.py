# utils/discord_notifier.py

import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, List
from config import Config

class DiscordNotifier:
    def __init__(self):
        self.config = Config()
        self.webhook_url = self.config.DISCORD_WEBHOOK_URL
        self.rate_limit = 30
        self.message_queue = []
        self.last_sent = datetime.utcnow()
        
    async def send_webhook(self, data: Dict):
        async with aiohttp.ClientSession() as session:
            await session.post(self.webhook_url, json=data)
    
    async def send_embed(self, title: str, description: str, color: int, fields: List[Dict] = None):
        embed = {
            'title': title,
            'description': description,
            'color': color,
            'timestamp': datetime.utcnow().isoformat(),
            'fields': fields or []
        }
        
        await self.send_webhook({'embeds': [embed]})
    
    async def send_trade_alert(self, trade: Dict):
        color = 0x00ff00 if trade.get('profit', 0) > 0 else 0xff0000
        
        fields = [
            {'name': 'Type', 'value': trade.get('type', 'Unknown'), 'inline': True},
            {'name': 'Amount', 'value': f"{trade.get('amount', 0):.4f}", 'inline': True},
            {'name': 'Profit', 'value': f"${trade.get('profit', 0):.2f}", 'inline': True}
        ]
        
        if 'tx_hash' in trade:
            fields.append({'name': 'TX Hash', 'value': f"`{trade['tx_hash'][:10]}...`", 'inline': False})
        
        await self.send_embed(
            title='Trade Executed',
            description=f"Strategy: {trade.get('type', 'Unknown')}",
            color=color,
            fields=fields
        )
    
    async def send_error_alert(self, error: str):
        await self.send_embed(
            title='Error Occurred',
            description=error[:1000],
            color=0xff0000
        )
    
    async def send_startup_message(self, info: Dict):
        fields = [
            {'name': 'Wallet', 'value': f"`{info['wallet'][:10]}...{info['wallet'][-8:]}`", 'inline': False},
            {'name': 'Active Strategies', 'value': ', '.join(info['strategies']), 'inline': False}
        ]
        
        await self.send_embed(
            title='Bot Started',
            description='Trading bot successfully initialized',
            color=0x00ff00,
            fields=fields
        )
    
    async def send_shutdown_message(self, info: Dict):
        fields = [
            {'name': 'Total Profit', 'value': f"${info['total_profit']:.2f}", 'inline': True},
            {'name': 'Trades Executed', 'value': str(info['trades_executed']), 'inline': True}
        ]
        
        await self.send_embed(
            title='Bot Stopped',
            description='Trading bot shut down gracefully',
            color=0xffff00,
            fields=fields
        )
    
    async def send_performance_update(self, metrics: Dict):
        fields = [
            {'name': 'Uptime', 'value': f"{metrics['uptime'] / 3600:.1f} hours", 'inline': True},
            {'name': 'Total Profit', 'value': f"${metrics['total_profit']:.2f}", 'inline': True},
            {'name': 'Trades', 'value': str(metrics['trades_executed']), 'inline': True},
            {'name': 'Gas Spent', 'value': f"{metrics['gas_spent']:.4f} ETH", 'inline': True}
        ]
        
        await self.send_embed(
            title='Performance Update',
            description='Hourly performance metrics',
            color=0x0099ff,
            fields=fields
        )
    
    async def send_opportunity_alert(self, opportunity: Dict):
        fields = [
            {'name': 'Type', 'value': opportunity.get('type', 'Unknown'), 'inline': True},
            {'name': 'Expected Profit', 'value': f"${opportunity.get('expected_profit', 0):.2f}", 'inline': True},
            {'name': 'Spread', 'value': f"{opportunity.get('spread', 0) * 100:.2f}%", 'inline': True}
        ]
        
        await self.send_embed(
            title='Opportunity Found',
            description='Potential arbitrage opportunity detected',
            color=0xffff00,
            fields=fields
        )
    
    async def batch_messages(self):
        while True:
            if self.message_queue:
                time_since_last = (datetime.utcnow() - self.last_sent).total_seconds()
                
                if time_since_last >= 2:
                    message = self.message_queue.pop(0)
                    await self.send_webhook(message)
                    self.last_sent = datetime.utcnow()
            
            await asyncio.sleep(1)