from aiohttp import web
import json
import datetime
from pkg.internal.brokers import BrokerName, BrokerError
from pkg.storage import StorageError
import pydantic
from pkg.server.utils import get_service


router = web.RouteTableDef()


@router.get('/api/balance')
async def get_account_balance_handler(request: web.Request):
    service = get_service(request)
    username = request.query.get('username')
    if not username:
        return web.json_response({'message': 'username not found'})

    return web.json_response(
        {'balance': await service.get_account_balance(username)})


class AccountOut(pydantic.BaseModel):
    username: str
    broker: BrokerName


@router.get('/api/accounts')
async def get_accounts_handler(request: web.Request):
    service = get_service(request)
    accounts = list(map(lambda account: AccountOut(username=account.username, broker=account.broker).dict(),
                        await service.get_accounts()))

    return web.json_response(accounts)


@router.get('/api/stocks')
async def get_stocks_handler(request: web.Request):
    service = get_service(request)
    stock_name = request.query.get('label')
    if not stock_name:
        return web.json_response([])

    return web.json_response(await service.get_stock(stock_name))


class OrderIn(pydantic.BaseModel):
    username: str
    deadline: datetime.datetime

    count: int
    price: int
    isin: str

    @pydantic.validator('deadline')
    def check_if_exceeded(cls, value):
        deadline = value.replace(tzinfo=None)
        if deadline < datetime.datetime.utcnow():
            raise ValueError('deadline exceeded')
        return deadline


@router.post('/api/order')
async def order_api_handler(request: web.Request):
    service = get_service(request)
    data = OrderIn(**(await request.json()))

    await service.schedule_order(
        username=data.username,
        deadline=data.deadline,
        stock_count=data.count,
        stock_price=data.price,
        stock_isin=data.isin,
    )
    return web.json_response({'message': f'order scheduled for {data.deadline}'})


class BrokerLoginIn(pydantic.BaseModel):
    username: str
    password: str
    broker: BrokerName


@router.post('/api/login')
async def login_api_handler(request: web.Request):
    service = get_service(request)

    data = BrokerLoginIn(**(await request.json()))

    await service.login(
        data.broker, data.username, data.password)

    return web.json_response({'message': 'login successful'})
