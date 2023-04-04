import abc
import json
import pickle
import uuid
from typing import Dict

import aiohttp
import sqlalchemy
from sqlalchemy.exc import IntegrityError

from pkg.models import Account, Order, OrderStatus


class StorageError(Exception):
    ...


class DuplicateRecordError(StorageError):
    ...


class RecordNotFoundError(StorageError):
    ...


class AbstractStorage(abc.ABC):
    @abc.abstractmethod
    def add_order(self, order: Order):
        raise NotImplementedError

    @abc.abstractmethod
    def add_account(self, account: Account):
        raise NotImplementedError

    @abc.abstractmethod
    def refresh_account(self, username: str, cookies: aiohttp.CookieJar, headers: Dict[str, str]):
        raise NotImplementedError

    @abc.abstractmethod
    def get_account_by_username(self, username: str) -> Account:
        raise NotImplementedError


class SqliteStorage(AbstractStorage):
    def __init__(self, url) -> None:
        self.engine = sqlalchemy.create_engine(url, echo=False)
        self.metadata_obj = sqlalchemy.MetaData()

        self.account_schema = sqlalchemy.Table(
            "accounts",
            self.metadata_obj,
            sqlalchemy.Column("id", sqlalchemy.Uuid, primary_key=True),
            sqlalchemy.Column("username", sqlalchemy.String(100), unique=True),
            sqlalchemy.Column("password", sqlalchemy.String(100)),
            sqlalchemy.Column("broker", sqlalchemy.String(30)),
            sqlalchemy.Column("headers", sqlalchemy.JSON),
            sqlalchemy.Column("cookies", sqlalchemy.BLOB),
        )

        self.order_schema = sqlalchemy.Table(
            "orders",
            self.metadata_obj,
            sqlalchemy.Column("id", sqlalchemy.Uuid, primary_key=True),
            sqlalchemy.Column("broker", sqlalchemy.String(30)),
            sqlalchemy.Column("isin", sqlalchemy.String(50)),
            sqlalchemy.Column("count", sqlalchemy.Integer),
            sqlalchemy.Column("price", sqlalchemy.Integer),
            sqlalchemy.Column("status", sqlalchemy.String(30)),
        )

    def migrate(self):
        self.metadata_obj.create_all(self.engine)

    def serialize_cookies(self, cookies: aiohttp.CookieJar) -> bytes:
        return pickle.dumps(cookies._cookies, pickle.HIGHEST_PROTOCOL)

    def deserialize_cookies(self, data: bytes) -> aiohttp.CookieJar:
        cookies = aiohttp.CookieJar()
        cookies._cookies = pickle.loads(data)
        return cookies

    def add_order(self, order: Order):
        query = '''
            INSERT INTO 
                orders(id, broker, isin, count, price, status) 
            VALUES (
                :id, :broker, :isin, :count, :price, :status
            )
        '''

        with self.engine.begin() as conn:
            conn.execute(sqlalchemy.text(query), [{
                'id': order.id.bytes,
                'broker': order.broker,
                'isin': order.isin,
                'count': order.count,
                'price': order.price,
                'status': order.status,
            }]
            )

    def get_order_by_id(self, order_id: uuid.UUID) -> Order:
        query = '''
            SELECT 
                id, broker, isin, count, price, status 
            FROM 
                orders 
            WHERE id=:id
        '''

        with self.engine.connect() as conn:
            row = conn.execute(
                sqlalchemy.text(query), [{'id': order_id.bytes}]).fetchone()
            if not row:
                raise RecordNotFoundError(f'order by id {order_id} not found')

            return Order(
                id=uuid.UUID(bytes=row[0]),
                broker=row[1],
                isin=row[2],
                count=row[3],
                price=row[4],
                status=row[5]
            )

    def update_order_status(self, order_id: uuid.UUID, new_status: OrderStatus):
        query = '''
            UPDATE orders 
            SET status=:status
            WHERE id=:id
        '''

        with self.engine.begin() as conn:
            conn.execute(sqlalchemy.text(query), [{
                'id': order_id.bytes,
                'status': new_status,
            }])

    def add_account(self, account: Account):
        """ 
        Add account to database. 
        Will raise DuplicateRecordError
        """

        query = '''
            INSERT INTO 
                accounts(id, broker, username, password, headers, cookies) 
            VALUES (
                :id, :broker, :username, :password, :headers, :cookies
            )
        '''
        with self.engine.begin() as conn:
            try:
                conn.execute(sqlalchemy.text(query), [{
                    'id': account.id.bytes,
                    'broker': account.broker,
                    'username': account.username,
                    'password': account.password,
                    'headers': json.dumps(account.headers),
                    'cookies': self.serialize_cookies(account.cookies)
                }]
                )
                conn.commit()
            except IntegrityError as exc:
                raise DuplicateRecordError(exc)

    def refresh_account(self, username: str, cookies: aiohttp.CookieJar, headers: Dict[str, str]):
        query = '''
            UPDATE accounts
            SET
                cookies=:cookies,
                headers=:headers
            WHERE username=:username
        '''
        with self.engine.begin() as conn:
            conn.execute(sqlalchemy.text(query), [{
                'username': username,
                'cookies': self.serialize_cookies(cookies),
                'headers': json.dumps(headers),
            }])

    def get_account_by_username(self, username: str) -> Account:
        query = '''
            SELECT 
                id, broker, username, password, headers, cookies
            FROM 
                accounts
            WHERE username=:username
        '''
        with self.engine.connect() as conn:
            row = conn.execute(
                sqlalchemy.text(query), [{'username': username}]).fetchone()
            if not row:
                raise ValueError("user not found")

            return Account(
                id=uuid.UUID(bytes=row[0]),
                broker=row[1],
                username=row[2],
                password=row[3],
                headers=json.loads(row[4]),
                cookies=self.deserialize_cookies(row[5]),
            )
