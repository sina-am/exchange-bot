import asyncio
import datetime
import json
import logging
import io
from typing import Dict, Tuple, Union
from urllib.parse import urlencode

import aiohttp
from yarl import URL

from pkg.internal.brokers.abc import AbstractBroker
from pkg.internal.brokers.exceptions import AuthenticationError
from pkg.internal.captcha import CaptchaSolver
from pkg.internal.requests import Request, schedule_request, calc_latency

logger = logging.getLogger('myapp')


class TavanaBroker(AbstractBroker):
    def __init__(self, captcha_ml: CaptchaSolver):
        self.name = "TAVANA"
        self.base_url = URL('https://onlinetavana.ir/')
        self.base_api_url = URL('https://api.onlinetavana.ir/Web/V1/')
        self.captcha_url = self.base_url / 'Account/undefined/4051238/Account/Captcha'
        self.captcha_detector = captcha_ml

        self.base_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        }

    async def __get_captcha(self, cookies: aiohttp.CookieJar, headers: Dict[str, str]) -> int:
        url = self.base_url / 'Account/undefined/4051238/Account/Captcha'

        # TODO: fix Reader incompatibility with BytesIO
        captcha_img = io.BytesIO()

        async with aiohttp.ClientSession(cookie_jar=cookies, headers=headers) as session:
            async with session.get(url) as res:
                async for chunk in res.content.iter_chunked(1024):
                    captcha_img.write(chunk)

        captcha_img.seek(0, 0)
        return int(self.captcha_detector.predict(captcha_img))  # type: ignore

    async def get_stock(self, stock_name: str) -> Dict[str, str]:
        url = 'https://api.onlinetavana.ir/Web/V1/Symbol/GetSymbol?term=' + stock_name

        headers = {
            **self.base_headers,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36 RuxitSynthetic/1.0 v8570808866573625578 t1940058695426470036 ath1fb31b7a altpriv cvcv=2 smf=0',
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as response:
                return await response.json()

    async def login(self, username: str, password: str, user_agent: str) -> Tuple[Dict[str, str], aiohttp.CookieJar]:
        url = self.base_url / 'login'
        cookies = aiohttp.CookieJar()
        user_headers = {
            **self.base_headers,
            'User-Agent': user_agent,
        }

        credentials = {
            'username': username,
            'Password': password,
            'capcha': await self.__get_captcha(cookies, user_headers),
        }

        login_headers = {
            **user_headers,
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        async with aiohttp.ClientSession(cookie_jar=cookies, headers=login_headers) as session:
            async with session.post(url, data=urlencode(credentials)) as res:
                if not self.get_api_token(cookies):
                    raise AuthenticationError("can't authenticate user")
                return (user_headers, cookies)

    def get_api_token(self, cookies: aiohttp.CookieJar) -> Union[str, None]:
        filtered = cookies.filter_cookies(self.base_url)
        if filtered:
            token = filtered.get('__apitoken__')
            if token:
                return token.value

        return None

    async def get_account_balance(
        self,
        headers: Dict[str, str],
        cookies: aiohttp.CookieJar,
    ) -> int:

        url = self.base_api_url / 'Accounting/GetCustomerAccount'
        headers = {
            **headers,
            'Authorization': f'BasicAuthentication {self.get_api_token(cookies)}',
        }

        async with aiohttp.ClientSession(cookie_jar=cookies, headers=headers) as session:
            async with session.get(url) as res:
                if res.status == 200:
                    return self.convert_to_int((await res.json())['Data'][0]['RealBalance'])
                elif res.status == 401:
                    raise AuthenticationError(
                        'got 401, please login again') from None
        raise ValueError("")

    def convert_to_int(self, str_number: str):
        return int(str_number.replace(',', ''))

    async def schedule_order(
        self,
        cookies: aiohttp.CookieJar,
        headers: Dict[str, str],
        deadline: datetime.datetime,
        isin: str,
        price: int,
        count: int = 1,
    ):

        url = self.base_api_url / 'Order/Post'
        headers = {
            **headers,
            'Authorization': f'BasicAuthentication {self.get_api_token(cookies)}',
            'Content-Type': 'application/json',
        }

        order_req = {
            'IsSymbolCautionAgreement': False,
            'CautionAgreementSelected': False,
            'FinancialProviderId': 1,
            'isin': isin,
            'IsSymbolSepahAgreement': False,
            'maxShow': 0,
            'minimumQuantity': 0,
            'orderCount': count,
            'orderId': 0,
            'orderPrice': price,
            'orderSide': '65',
            'orderValidity': 74,
            'orderValiditydate': None,
            'SepahAgreementSelected': False,
            'shortSellIncentivePercent': 0,
            'shortSellIsEnabled': False,
        }

        request = Request(
            method='post',
            url=url,
            headers=headers,
            data=json.dumps(order_req).encode()
        )
        # check network traffic from time to 1 minute before deadline
        logger.debug("checking latency...")
        while datetime.datetime.utcnow() + datetime.timedelta(minutes=3) < deadline:
            latency = await calc_latency('get', self.base_api_url)
            logger.debug(f"got latency: {latency}")
            self.update_latencies(latency)
            await asyncio.sleep(30)

        logger.debug(f"sending request with latency of {self.min_latency}")
        async with schedule_request(request, deadline, self.min_latency) as response:
            return response.status, await response.text()
