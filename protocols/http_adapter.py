"""
    POST /api/v1/ingest приём телеметрии
    POST /api/v1/devices/register регистрация устройства
    GET /api/v1/health чек
"""

import asyncio
from aiohttp import web
import json
from typing import Any

from models.message import Message, MessageType
from protocols.adapter import ProtocolAdapter


class HTTPAdapter(ProtocolAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.host = "0.0.0.0"
        self.port = 8081
        self.webhook = "/api/v1/ingest"

        # self.app = None
        # self.runner = None

    @property
    def protocol_name(self) -> str:
        return "http"

    async def start(self) -> None:
        self.app = web.Application()
        self.app.router.add_post(
            self.webhook,
            self.handle_ingest
        )
        self.app.router.add_post(
            "/api/v1/devices/register",
            self.handle_register
        )
        self.app.router.add_get(
            "/api/v1/health",
            self.handle_health
        )

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()

        self.running = True
        print("HTTP adapter listening on %s:%d", self.host, self.port)

    async def stop(self) -> None:
        """Остановить HTTP-сервер."""
        self.running = False
        if self.runner:
            await self.runner.cleanup()
        print("HTTP adapter stopped")

    async def handle_ingest(self, request) -> Any:
        """Приём телеметрии."""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        device_id = body.get("device_id")
        if not device_id:
            return web.json_response(
                {"error": "device_id required"},
                status=400
            )

        message = Message(
            message_type=MessageType.TELEMETRY,
            device_id=device_id,
            protocol="http",
            message_topic=self.webhook,
            payload=body.get("data", body),
        )

        await self.publish_message(f"telemetry.{device_id}", message)

        return web.json_response({
            "status": "accepted",
            "message_id": message.message_id,
        }, status=202)

    async def handle_register(self, request) -> Any:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        message = Message(
            message_type=MessageType.REGISTRATION,
            device_id=body.get("device_id", ""),
            protocol="http",
            message_topic="/api/v1/devices/register",
            payload=body,
        )

        await self.publish_message(
            f"device.register.{message.device_id}",
            message)

        return web.json_response({"status": "registered"}, status=201)

    async def handle_health(self, request) -> Any:
        health = await self.health_check()
        return web.json_response(health)
