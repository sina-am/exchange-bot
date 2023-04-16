from aiohttp.connector import Connection
from contextlib import asynccontextmanager
import abc
import asyncio
import datetime
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from aiohttp import ClientRequest, ClientTimeout, TCPConnector
from yarl import URL

logger = logging.getLogger('myapp')


class AbstractRequest(abc.ABC):
    @abc.abstractmethod
    async def make_connection(self):
        raise NotImplementedError

    @abc.abstractmethod
    async def send(self, conn: Connection):
        raise NotImplementedError


class Request(AbstractRequest):
    def __init__(
            self,
            method: str,
            url: Union[URL, str],
            headers: Optional[Dict[str, str]] = None,
            data: Optional[bytes] = None,
    ) -> None:

        if isinstance(url, str):
            url = URL(url)
        self.request = ClientRequest(
            method=method,
            url=url,
            headers=headers,
            data=data,
        )

    @asynccontextmanager
    async def make_connection(self):
        async with TCPConnector() as connector:
            conn = await connector.connect(self.request, [], ClientTimeout(total=30))
            conn.protocol.set_response_params(  # type: ignore
                read_until_eof=True,
                auto_decompress=True,
                read_timeout=10,
                read_bufsize=1024,
            )
            yield conn

    @asynccontextmanager
    async def send(self, conn: Connection):
        async with await self.request.send(conn) as response:
            await response.start(conn)
            yield response


async def calc_latency(method: str, url: Union[URL, str]) -> float:
    """ Calculate latency for a specific url. """
    request = Request(method=method, url=url)
    async with request.make_connection() as conn:
        t1 = time.time()
        async with request.send(conn) as _:
            t2 = time.time()
        return (t2 - t1) * .5  # Because it's actually a the latency of send plus recv time


@asynccontextmanager
async def schedule_request(request: Request, deadline: datetime.datetime, latency: float = 0):
    """ Schedule request for the deadline 
    latency: send request at deadline - latency time 
    NODE: latency should be calculated by calc_latency function
    """

    logger.info(f"request scheduled for deadline: {deadline}")
    await _go_to_deep_sleep(deadline)

    logger.info("making tcp connection")
    async with request.make_connection() as conn:
        logger.info("connection is ready. waiting for deadline")
        time_to_send = deadline - datetime.timedelta(seconds=latency)
        logger.info(f"request will send at {time_to_send}")
        await _go_to_shallow_sleep(time_to_send)

        logger.info(f"request sended at {datetime.datetime.utcnow()}")
        t1 = time.time()
        async with request.send(conn) as response:
            t2 = time.time()
            logger.info(
                f"latency: {t2 - t1}s")
            yield response


async def _go_to_deep_sleep(deadline: datetime.datetime):
    """ Will awake 5 second before deadline """
    sleep_time = (
        deadline - datetime.timedelta(seconds=5)) - datetime.datetime.utcnow()
    await asyncio.sleep(sleep_time.total_seconds())


async def _go_to_shallow_sleep(deadline: datetime.datetime):
    """ Will awake at deadline """
    sleep_time = (deadline - datetime.datetime.utcnow()).total_seconds()
    if sleep_time > 1:
        await asyncio.sleep(sleep_time - 1)

    counter = 0
    while datetime.datetime.utcnow() < deadline:
        counter += 1
