import aiohttp
import json
from datetime import datetime, timezone

class DiscordNotifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
        self.enabled = bool(webhook_url)
    
    async def send_alert(self, title, description, color=0x00ff00, fields=None):
        if not self.enabled:
            return
        
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fields": fields or []
        }
        
        payload = {"embeds": [embed]}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    return response.status == 204
        except Exception as e:
            print(f"Discord notification failed: {e}")
            return False
