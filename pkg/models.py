import uuid
from dataclasses import dataclass
from typing import Dict, Literal
import datetime

import aiohttp

from pkg.internal.brokers.abc import BrokerName

OrderStatus = Literal["SCHEDULED", "DONE"]


@dataclass
class Account:
    id: uuid.UUID
    broker: BrokerName
    username: str
    password: str
    last_login: datetime.datetime

    cookies: aiohttp.CookieJar
    headers: Dict[str, str]


@dataclass
class Order:
    id: uuid.UUID
    broker: BrokerName
    isin: str
    count: int
    price: int
    status: OrderStatus
