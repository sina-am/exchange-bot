import abc
import datetime
import aiohttp
from typing import Dict, Literal, Tuple


BrokerName = Literal["TAVANA", "FAKE"]


class AbstractBroker(abc.ABC):
    name: BrokerName
    min_latency: float = 0
    max_latency: float = 0
    avg_latency: float = 0

    def update_latencies(self, new_latency: float):
        if new_latency > self.max_latency:
            self.max_latency = new_latency
        if new_latency < self.min_latency or self.min_latency == 0:
            self.min_latency = new_latency

        self.avg_latency = (self.avg_latency + new_latency) / 2

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
