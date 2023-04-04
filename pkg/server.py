import datetime
import json
import logging
import uuid
from typing import Dict

import pydantic
from aiohttp import web

from pkg.internal.brokers import BrokerError
from pkg.models import BrokerName
from pkg.service import Service
from pkg.storage import StorageError


class BrokerLoginIn(pydantic.BaseModel):
    username: str
    password: str
    broker: BrokerName


class OrderIn(pydantic.BaseModel):
    username: str
    deadline: datetime.datetime

    order_count: int
    order_price: int
    order_isin: str


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class WebServer:
    def __init__(
        self,
        host: str,
        port: int,
        service: Service
    ) -> None:

        self.host = host
        self.port = port
        self.service = service
        self.app = web.Application()

    def run(self):
        self.app.add_routes([
            web.post('/api/login', self.login_api_handler),
            web.post('/api/order', self.order_api_handler),
            web.get('/api/balance', self.get_account_balance_handler),
        ])

        logger.info(f"server is running on http://{self.host}:{self.port}")
        web.run_app(self.app, host=self.host, print=lambda _: None,
                    port=self.port, reuse_address=True)
        logger.info(f"server is shutting down")

    async def get_account_balance_handler(self, request: web.Request):
        username = request.query.get('username')
        if not username:
            return web.json_response({'message': 'username not found'})

        return web.json_response(
            {'balance': await self.service.get_account_balance(username)})

    async def order_api_handler(self, request: web.Request):
        try:
            data = OrderIn(**(await request.json()))
        except json.JSONDecodeError as exc:
            return web.json_response({'message': 'invalid json'}, status=400)
        except pydantic.ValidationError as exc:
            return web.json_response(text=exc.json(), status=400)

        await self.service.schedule_order(
            username=data.username,
            deadline=data.deadline,
            stock_count=data.order_count,
            stock_price=data.order_price,
            stock_isin=data.order_isin,
        )
        return web.json_response({'message': f'order scheduled for {data.deadline}'})

    async def login_api_handler(self, request: web.Request):
        try:
            data = BrokerLoginIn(**(await request.json()))
        except json.JSONDecodeError as exc:
            return web.json_response({'message': 'invalid json'}, status=400)
        except pydantic.ValidationError as exc:
            return web.json_response(text=exc.json(), status=400)

        try:
            await self.service.login(
                data.broker, data.username, data.password)
        except BrokerError as exc:
            return web.json_response({'message': f'broker said: {str(exc)}'}, status=400)
        except StorageError as exc:
            return web.json_response({'message': f'{str(exc)}'}, status=400)

        return web.json_response({'message': 'login successful'})
