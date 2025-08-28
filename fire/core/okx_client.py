# core/okx_client.py

import asyncio
import hmac
import base64
import time
import json
from datetime import datetime
from typing import Dict, List, Optional
import aiohttp
import websockets
from config import Config

class OKXClient:
    def __init__(self):
        self.config = Config()
        self.base_url = "https://www.okx.com"
        self.ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.ws_private_url = "wss://ws.okx.com:8443/ws/v5/private"
        self.session = None
        self.ws = None
        self.orderbook = {}
        self.balances = {}
        
    async def connect(self):
        self.session = aiohttp.ClientSession()
        await self.connect_websocket()
        asyncio.create_task(self.maintain_websocket())
        
    async def disconnect(self):
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
    
    def generate_signature(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.config.OKX_SECRET_KEY, encoding='utf8'),
            bytes(message, encoding='utf8'),
            digestmod='sha256'
        )
        return base64.b64encode(mac.digest()).decode()
    
    def get_headers(self, method: str, request_path: str, body: str = '') -> Dict:
        timestamp = datetime.utcnow().isoformat()[:-3] + 'Z'
        signature = self.generate_signature(timestamp, method, request_path, body)
        
        return {
            'OK-ACCESS-KEY': self.config.OKX_API_KEY,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.config.OKX_PASSPHRASE,
            'Content-Type': 'application/json'
        }
    
    async def connect_websocket(self):
        self.ws = await websockets.connect(self.ws_url)
        
        subscribe_msg = {
            "op": "subscribe",
            "args": [
                {"channel": "tickers", "instId": "ETH-USDT"},
                {"channel": "tickers", "instId": "BTC-USDT"},
                {"channel": "books5", "instId": "ETH-USDT"},
                {"channel": "books5", "instId": "BTC-USDT"}
            ]
        }
        
        await self.ws.send(json.dumps(subscribe_msg))
        asyncio.create_task(self.process_websocket_messages())
    
    async def process_websocket_messages(self):
        while self.ws:
            try:
                message = await self.ws.recv()
                data = json.loads(message)
                
                if 'data' in data:
                    await self.handle_market_data(data)
                    
            except websockets.exceptions.ConnectionClosed:
                await self.reconnect_websocket()
            except Exception as e:
                print(f"WebSocket error: {e}")
                await asyncio.sleep(1)
    
    async def handle_market_data(self, data: Dict):
        channel = data.get('arg', {}).get('channel')
        
        if channel == 'books5':
            inst_id = data['arg']['instId']
            self.orderbook[inst_id] = {
                'bids': [[float(p), float(q)] for p, q, _, _ in data['data'][0]['bids']],
                'asks': [[float(p), float(q)] for p, q, _, _ in data['data'][0]['asks']],
                'timestamp': int(data['data'][0]['ts'])
            }
    
    async def reconnect_websocket(self):
        await asyncio.sleep(5)
        try:
            await self.connect_websocket()
        except Exception as e:
            print(f"Failed to reconnect: {e}")
            await self.reconnect_websocket()
    
    async def maintain_websocket(self):
        while True:
            await asyncio.sleep(20)
            if self.ws:
                try:
                    await self.ws.send(json.dumps({"op": "ping"}))
                except:
                    await self.reconnect_websocket()
    
    async def get_balance(self) -> Dict[str, float]:
        request_path = "/api/v5/account/balance"
        headers = self.get_headers("GET", request_path)
        
        async with self.session.get(
            f"{self.base_url}{request_path}",
            headers=headers
        ) as response:
            data = await response.json()
            
            if data['code'] == '0':
                balances = {}
                for detail in data['data'][0]['details']:
                    if float(detail['availBal']) > 0:
                        balances[detail['ccy']] = float(detail['availBal'])
                return balances
            
            raise Exception(f"Failed to get balance: {data['msg']}")
    
    async def place_order(self, inst_id: str, side: str, size: float, price: Optional[float] = None) -> str:
        request_path = "/api/v5/trade/order"
        
        order_data = {
            "instId": inst_id,
            "tdMode": "cash",
            "side": side,
            "ordType": "market" if price is None else "limit",
            "sz": str(size)
        }
        
        if price:
            order_data["px"] = str(price)
        
        body = json.dumps(order_data)
        headers = self.get_headers("POST", request_path, body)
        
        async with self.session.post(
            f"{self.base_url}{request_path}",
            headers=headers,
            data=body
        ) as response:
            data = await response.json()
            
            if data['code'] == '0':
                return data['data'][0]['ordId']
            
            raise Exception(f"Failed to place order: {data['msg']}")
    
    async def cancel_order(self, inst_id: str, order_id: str) -> bool:
        request_path = "/api/v5/trade/cancel-order"
        
        body = json.dumps({
            "instId": inst_id,
            "ordId": order_id
        })
        
        headers = self.get_headers("POST", request_path, body)
        
        async with self.session.post(
            f"{self.base_url}{request_path}",
            headers=headers,
            data=body
        ) as response:
            data = await response.json()
            return data['code'] == '0'
    
    async def get_order_status(self, inst_id: str, order_id: str) -> Dict:
        request_path = f"/api/v5/trade/order?instId={inst_id}&ordId={order_id}"
        headers = self.get_headers("GET", request_path)
        
        async with self.session.get(
            f"{self.base_url}{request_path}",
            headers=headers
        ) as response:
            data = await response.json()
            
            if data['code'] == '0' and data['data']:
                return {
                    'status': data['data'][0]['state'],
                    'filled_size': float(data['data'][0]['fillSz']),
                    'avg_price': float(data['data'][0]['avgPx']) if data['data'][0]['avgPx'] else 0
                }
            
            return {'status': 'unknown', 'filled_size': 0, 'avg_price': 0}
    
    async def get_ticker(self, inst_id: str) -> Dict:
        request_path = f"/api/v5/market/ticker?instId={inst_id}"
        
        async with self.session.get(f"{self.base_url}{request_path}") as response:
            data = await response.json()
            
            if data['code'] == '0' and data['data']:
                return {
                    'bid': float(data['data'][0]['bidPx']),
                    'ask': float(data['data'][0]['askPx']),
                    'last': float(data['data'][0]['last']),
                    'volume': float(data['data'][0]['vol24h'])
                }
            
            raise Exception(f"Failed to get ticker: {data.get('msg', 'Unknown error')}")
    
    def get_orderbook_snapshot(self, inst_id: str) -> Dict:
        return self.orderbook.get(inst_id, {'bids': [], 'asks': [], 'timestamp': 0})