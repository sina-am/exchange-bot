import datetime
import unittest
from pkg.internal.requests import ScheduledRequest


class ScheduledRequestTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.req = ScheduledRequest(
            method='GET',
            url='https://www.google.com/',
            deadline=datetime.datetime.utcnow() + datetime.timedelta(seconds=3)
        )

    async def test_scheduled(self):
        status, data = await self.req.run()
        assert status == 200
