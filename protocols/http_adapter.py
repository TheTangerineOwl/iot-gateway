"""
    POST /api/v1/ingest приём телеметрии
    POST /api/v1/devices/register регистрация устройства
    GET /api/v1/health чек
"""
from aiohttp import web
from http import HTTPStatus
import json
import logging
from typing import Any

from models.message import Message, MessageType
from protocols.adapter import ProtocolAdapter


logger = logging.getLogger(__name__)


class HTTPAdapter(ProtocolAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.host = "0.0.0.0"
        self.port = 8081
        self.webhook = "/api/v1/ingest"

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
        logger.info(
            "HTTP adapter listening on %s:%d",
            self.host, self.port
        )

    async def stop(self) -> None:
        """Остановить HTTP-сервер."""
        self.running = False
        if self.runner:
            await self.runner.cleanup()
        logger.info("HTTP adapter stopped")

    async def handle_ingest(self, request) -> Any:
        """Приём телеметрии."""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                {"error": "Invalid JSON"},
                status=HTTPStatus.BAD_REQUEST
            )

        device_id = body.get("device_id")
        if not device_id:
            return web.json_response(
                {"error": "device_id required"},
                status=HTTPStatus.BAD_REQUEST
            )

        message = Message(
            message_type=MessageType.TELEMETRY,
            device_id=device_id,
            protocol="http",
            message_topic=self.webhook,
            payload=body.get("data", body),
        )

        await self.publish_message(f"telemetry.{device_id}", message)

        # logger.debug('HTTP adapter got telemetry: %s', message.to_dict())

        return web.json_response({
            "status": "accepted",
            "message_id": message.message_id,
            },
            status=HTTPStatus.ACCEPTED
        )

    async def handle_register(self, request) -> Any:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                {"error": "Invalid JSON"},
                status=HTTPStatus.BAD_REQUEST
            )

        message = Message(
            message_type=MessageType.REGISTRATION,
            device_id=body.get("device_id", ""),
            protocol="http",
            message_topic="/api/v1/devices/register",
            payload=body,
        )
        # message.message_topic = f"device.register.{message.device_id}"
        await self.publish_message(
            f"device.register.{message.device_id}",
            message
        )

        # logger.debug('HTTP adapter got register: %s', message.to_dict())

        return web.json_response(
            {"status": "registered"},
            status=HTTPStatus.CREATED
        )

    async def handle_health(self, request) -> Any:
        health = await self.health_check()

        # json = await request.json()
        # if json:
        #     id = str(json.get('device_id', ''))
        #     if len(id) > 0:
        #         logger.debug('Health check from device %s', id)

        # logger.debug('HTTP got health check')

        return web.json_response(health)
