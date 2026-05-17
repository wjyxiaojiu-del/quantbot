import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # symbol -> set of websockets
        self.subscriptions: Dict[str, Set[WebSocket]] = {}
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)
        for subs in self.subscriptions.values():
            subs.discard(ws)

    def subscribe(self, ws: WebSocket, symbol: str):
        if symbol not in self.subscriptions:
            self.subscriptions[symbol] = set()
        self.subscriptions[symbol].add(ws)

    def unsubscribe(self, ws: WebSocket, symbol: str):
        if symbol in self.subscriptions:
            self.subscriptions[symbol].discard(ws)

    async def broadcast(self, symbol: str, data: dict):
        if symbol not in self.subscriptions:
            return
        dead = []
        for ws in self.subscriptions[symbol]:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@router.websocket("/quotes")
async def websocket_quotes(ws: WebSocket):
    """
    实时行情 WebSocket
    客户端发送: {"action": "subscribe", "symbol": "000001.SZ"}
    客户端发送: {"action": "unsubscribe", "symbol": "000001.SZ"}
    服务端推送: {"symbol": "000001.SZ", "data": {...}}
    """
    await manager.connect(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"error": "无效的 JSON"})
                continue

            action = msg.get("action")
            symbol = msg.get("symbol")

            if action == "subscribe" and symbol:
                manager.subscribe(ws, symbol)
                await ws.send_json({"action": "subscribed", "symbol": symbol})
            elif action == "unsubscribe" and symbol:
                manager.unsubscribe(ws, symbol)
                await ws.send_json({"action": "unsubscribed", "symbol": symbol})
            elif action == "ping":
                await ws.send_json({"action": "pong"})
            else:
                await ws.send_json({"error": "未知操作"})
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(ws)


async def push_quote(symbol: str, data: dict):
    """供其他模块调用：推送行情数据"""
    await manager.broadcast(symbol, {"symbol": symbol, "data": data, "type": "quote"})
