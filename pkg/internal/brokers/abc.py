import abc
import datetime
from typing import Dict, Tuple

import aiohttp


class AbstractBroker(abc.ABC):
    name: str 
    min_latency: float = 0
    max_latency: float = 0
    avg_latency: float = 0

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
