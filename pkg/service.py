
import asyncio
import datetime
import logging
import uuid
from typing import Dict

from pkg.internal.brokers import AbstractBroker
from pkg.models import Account, BrokerName, Order
from pkg.storage import AbstractStorage, RecordNotFoundError

logger = logging.getLogger('myapp')
logger.setLevel(logging.INFO)


class Service:
    def __init__(self, storage: AbstractStorage, brokers: Dict[BrokerName, AbstractBroker]) -> None:
        self.storage = storage
        self.brokers = brokers

    def get_broker(self, name: BrokerName) -> AbstractBroker:
        broker = self.brokers.get(name)
        if not broker:
            raise KeyError('invalid broker name')
        return broker

    async def get_random_user_agent(self) -> str:
        return 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/111.0'

    async def get_account_balance(self, username: str) -> int:
        account = self.storage.get_account_by_username(username)
        broker = self.get_broker(account.broker)
        return await broker.get_account_balance(account.headers, account.cookies)

    async def login(self, broker_name: BrokerName, username: str, password: str) -> Account:
        """
        raises: AuthenticationError
        """
        broker = self.get_broker(broker_name)

        headers, cookies = await broker.login(
            username=username,
            password=password,
            user_agent=await self.get_random_user_agent(),
        )

        try:
            account = self.storage.get_account_by_username(username)
            self.storage.refresh_account(username, cookies, headers)
        except RecordNotFoundError:
            account = Account(
                id=uuid.uuid4(),
                broker=broker_name,
                username=username,
                password=password,
                cookies=cookies,
                headers=headers,
            )

            self.storage.add_account(account)

        return account

    async def schedule_order(
            self,
            username: str,
            stock_isin: str,
            stock_count: int,
            stock_price: int,
            deadline: datetime.datetime
    ):
        """ 
        raises: AccountNotFound
        """

        account = self.storage.get_account_by_username(username)
        broker = self.get_broker(account.broker)

        order = Order(
            id=uuid.uuid4(),
            broker=account.broker,
            isin=stock_isin,
            count=stock_count,
            price=stock_price,
            status='SCHEDULED',
        )

        # self.storage.add_order(order)

        asyncio.create_task(
            self.__schedule_order_worker(broker, account, order, deadline))
        logger.info(f"task scheduled for {deadline}")

    async def __schedule_order_worker(
        self,
        broker: AbstractBroker,
        account: Account,
        order: Order,
        deadline: datetime.datetime
    ):

        status, data = await broker.schedule_order(
            account.cookies,
            account.headers,
            deadline,
            order.isin,
            order.price,
            order.count
        )
        logger.info(f"broker sends {status}, {data}")
        if status == 200:
            logger.info(f"order {order.id} committed ")
