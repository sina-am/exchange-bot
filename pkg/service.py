import asyncio
import datetime
import logging
import uuid
from typing import Dict, Iterable

from pkg.internal.brokers import AbstractBroker, BrokerName
from pkg.internal.brokers.exceptions import AuthenticationError
from pkg.models import Account, Order
from pkg.storage import AbstractStorage, RecordNotFoundError

logger = logging.getLogger('myapp')


class Service:
    def __init__(self, storage: AbstractStorage, brokers: Dict[BrokerName, AbstractBroker]) -> None:
        self.storage = storage
        self.brokers = brokers

    def get_broker(self, name: BrokerName) -> AbstractBroker:
        self.storage
        broker = self.brokers.get(name)
        if not broker:
            raise KeyError('invalid broker name')
        return broker

    async def get_random_user_agent(self) -> str:
        return 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/111.0'

    async def get_accounts(self) -> Iterable[Account]:
        return self.storage.get_accounts()

    async def get_account_balance(self, username: str) -> int:
        account = self.storage.get_account_by_username(username)
        broker = self.get_broker(account.broker)
        return await broker.get_account_balance(account.headers, account.cookies)

    async def get_stock(self, stock_name: str) -> Dict[str, str]:
        broker = self.get_broker('TAVANA')
        return await broker.get_stock(stock_name)

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
            self.storage.refresh_account(username, datetime.datetime.utcnow(), cookies, headers)
        except RecordNotFoundError:
            account = Account(
                id=uuid.uuid4(),
                broker=broker_name,
                username=username,
                password=password,
                last_login=datetime.datetime.utcnow(),
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

        self.storage.add_order(order)

        asyncio.create_task(
            self.__schedule_order_worker(broker, account, order, deadline))
        logger.info(f"task scheduled for {deadline}")

    async def __attempt_for_login(self, broker_name: BrokerName, username: str, password: str) -> Account:
        """ Try to login the account. but since captcha solver might not work every time.
        It'll attempt to login 3 times and if all fail then raise AuthenticationError
        """

        for n_attempts in range(3):
            try:
                return await self.login(broker_name, username, password)
            except AuthenticationError:
                logger.warning(f"{n_attempts} attempt for logging the {username} failed")
                await asyncio.sleep(5)
        raise AuthenticationError

    async def __schedule_order_worker(
        self,
        broker: AbstractBroker,
        account: Account,
        order: Order,
        deadline: datetime.datetime
    ):
        logger.debug("going to deep sleep...")
        await asyncio.sleep((deadline - datetime.datetime.utcnow() - datetime.timedelta(minutes=15)).total_seconds())
        logger.debug(f"I'm awake. it's {(deadline - datetime.datetime.utcnow()).seconds//60}minutes before deadline")

        logger.debug("let's see if last_login was for more than 15 minutes ago")
        if (account.last_login + datetime.timedelta(minutes=15)) < datetime.datetime.utcnow():
            logger.debug("yes it was. refreshing token")
            account = await self.__attempt_for_login(broker.name, account.username, account.password)
        else:
            logger.debug("nope. we're ready to go")

        status, data = await broker.schedule_order(
            cookies=account.cookies,
            headers=account.headers,
            deadline=deadline,
            isin=order.isin,
            price=order.price,
            count=order.count,
        )
        logger.info(f"broker sends {status}, {data}")
        if status == 200:
            logger.info(f"order {order.id} committed ")
