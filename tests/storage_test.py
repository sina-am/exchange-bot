import unittest
import uuid

import aiohttp
from yarl import URL

from pkg.models import Account, Order

from pkg.storage import (
    DuplicateRecordError,
    RecordNotFoundError,
    SqliteStorage
)


class StorageTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.storage = SqliteStorage('sqlite+pysqlite:///:memory:')
        self.storage.migrate()

    def test_add_order(self):
        order = Order(
            id=uuid.uuid4(),
            broker='FAKE',
            isin='IRFake',
            count=1,
            price=1,
            status='SCHEDULED'
        )

        self.storage.add_order(order)

        self.assertEqual(order, self.storage.get_order_by_id(order.id))

    def test_update_order_status(self):
        order = Order(
            id=uuid.uuid4(),
            broker='FAKE',
            isin='IRFake',
            count=1,
            price=1,
            status='SCHEDULED'
        )

        self.storage.add_order(order)

        self.storage.update_order_status(order.id, 'DONE')

        self.assertEqual(self.storage.get_order_by_id(order.id).status, 'DONE')

    def test_get_none_existent_order(self):
        with self.assertRaises(RecordNotFoundError):
            self.storage.get_order_by_id(uuid.uuid4())

    def test_refresh_account_cookies(self):
        account = Account(
            id=uuid.uuid4(),
            broker='FAKE',
            username='1234',
            password='1234',
            cookies=aiohttp.CookieJar(),
            headers={
                'User-Agent': 'python3.10',
                'Set-Cookie': 'something=something'
            },
        )

        self.storage.add_account(account)

        account.cookies.update_cookies(
            response_url=URL('test.com'),
            cookies={
                'key': '1234'
            }
        )

        self.storage.refresh_account(
            account.username, account.cookies, account.headers)

        db_cookies = self.storage.get_account_by_username(
            account.username).cookies.filter_cookies(URL('test.com'))

        self.assertEqual(
            db_cookies, account.cookies.filter_cookies(URL('test.com')))

    def test_refresh_account_headers(self):
        account = Account(
            id=uuid.uuid4(),
            broker='FAKE',
            username='1234',
            password='1234',
            cookies=aiohttp.CookieJar(),
            headers={
                'User-Agent': 'python3.10',
                'Set-Cookie': 'something=something'
            },
        )

        self.storage.add_account(account)

        account.headers.update({
            'User-Agent': 'python3.11',
        })

        self.storage.refresh_account(
            account.username, account.cookies, account.headers)

        self.assertEqual(
            self.storage.get_account_by_username(account.username).headers,
            account.headers
        )

    def test_add_account(self):
        account = Account(
            id=uuid.uuid4(),
            broker='FAKE',
            username='1234',
            password='1234',
            cookies=aiohttp.CookieJar(),
            headers={
                'User-Agent': 'python3.10',
                'Set-Cookie': 'something=something'
            },
        )

        self.storage.add_account(account)
        db_account = self.storage.get_account_by_username(account.username)
        assert account.id == db_account.id
        assert account.broker == db_account.broker
        assert account.username == db_account.username
        assert account.password == db_account.password
        assert account.headers == db_account.headers
        # Check actual value not pointer address
        assert account.cookies._cookies == db_account.cookies._cookies

    def test_add_duplicate_account(self):
        account = Account(
            id=uuid.uuid4(),
            broker='FAKE',
            username='1234',
            password='1234',
            cookies=aiohttp.CookieJar(),
            headers={},
        )

        self.storage.add_account(account)

        account_dup = Account(
            id=uuid.uuid4(),
            broker='TAVANA',
            username='1234',
            password='1111',
            cookies=aiohttp.CookieJar(),
            headers={},
        )
        with self.assertRaises(DuplicateRecordError):
            self.storage.add_account(account_dup)
