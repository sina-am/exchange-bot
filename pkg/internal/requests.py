import asyncio
import datetime
import logging
import time
from typing import Dict, Optional, Union

from aiohttp import ClientRequest, ClientTimeout, TCPConnector
from yarl import URL

logger = logging.getLogger('myapp')
logger.setLevel(logging.DEBUG)


class ScheduledRequest:
    def __init__(
            self,
            method: str,
            url: Union[URL, str],
            deadline: datetime.datetime,
            headers: Optional[Dict[str, str]] = None,
            data: Optional[bytes] = None,
            timeout: int = 10,
    ):
        if isinstance(url, str):
            url = URL(url)
        self.deadline = deadline
        self.req = ClientRequest(
            method=method,
            url=url,
            headers=headers,
            data=data,
        )

        self.timeout = timeout

    async def run(self):
        self.connector = TCPConnector(
            force_close=True,
            limit=1,
            verify_ssl=True,
            ssl=True
        )
        # Calculate time to sleep (on_time - timeout/2)
        # Wait till it's time to make the tcp connection (timeout/2 second before deadline)
        logger.info(f"request scheduled for deadline: {self.deadline}")
        sleep_time = (
            self.deadline - datetime.timedelta(seconds=self.timeout/2)) - datetime.datetime.now()
        await asyncio.sleep(sleep_time.total_seconds())

        logger.info("making tcp connection")
        conn = await self.connector.connect(self.req, [], ClientTimeout())
        logger.info("connection is ready. waiting for deadline")

        conn.protocol.set_response_params(
            read_until_eof=True,
            auto_decompress=True,
            read_timeout=10,
            read_bufsize=1024,
        )
        sleep_time2 = self.deadline - datetime.datetime.now()
        await asyncio.sleep(sleep_time2.total_seconds() - 1)
        i = 0
        while datetime.datetime.now() < self.deadline:
            i += 1

        logger.info(f"request sended at {datetime.datetime.now()}")
        t1 = time.time_ns()
        resp = await self.req.send(conn)
        t2 = time.time_ns()
        logger.info(
            f"latency using {self.__class__.__name__}: {t2 - t1}ns")

        await resp.start(conn)
        data = resp.status, await resp.text()
        resp.close()
        await self.req.close()
        conn.close()
        return data
