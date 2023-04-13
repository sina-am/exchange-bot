import abc
import datetime
import aiohttp
from typing import Dict, Literal, Tuple


BrokerName = Literal["TAVANA", "FAKE"]


class AbstractBroker(abc.ABC):
    name: BrokerName

    @abc.abstractmethod
    async def get_stock(self, stock_name: str) -> Dict[str, str]:
        raise NotImplementedError

    @abc.abstractmethod
    async def login(
            self,
            username: str,
            password: str,
            user_agent: str
    ) -> Tuple[Dict[str, str], aiohttp.CookieJar]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_account_balance(
        self,
        headers: Dict[str, str],
        cookies: aiohttp.CookieJar,
    ) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    async def schedule_order(
        self,
        cookies: aiohttp.CookieJar,
        headers: Dict[str, str],
        deadline: datetime.datetime,
        isin: str,
        price: int,
        count: int = 1,
    ):
        raise NotImplementedError
