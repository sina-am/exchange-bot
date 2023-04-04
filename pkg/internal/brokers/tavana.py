import datetime
import json
import logging
from typing import Dict, Tuple, Union
from urllib.parse import urlencode

import aiohttp
from yarl import URL

from pkg.internal.brokers.abc import AbstractBroker
from pkg.internal.brokers.exceptions import AuthenticationError
from pkg.internal.captcha import CaptchaML
from pkg.internal.requests import ScheduledRequest

logger = logging.getLogger('myapp')


class TavanaBroker(AbstractBroker):
    def __init__(self, captcha_ml: CaptchaML):
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

        async with aiohttp.ClientSession(cookie_jar=cookies, headers=headers) as session:
            async with session.get(url) as res:
                with open('./captcha.jpeg', 'wb') as fd:
                    async for chunk in res.content.iter_chunked(1024):
                        fd.write(chunk)

        return int(input('Enter captcha'))
        return int(self.captcha_detector.predict_captcha(img))

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

        req = ScheduledRequest(
            url=url,
            method='POST',
            data=json.dumps(order_req).encode(),
            headers=headers,
            deadline=deadline,
        )
        return await req.run()
