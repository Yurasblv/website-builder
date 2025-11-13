import asyncio
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp
from aiohttp import ClientResponseError
from cachetools import TTLCache
from loguru import logger
from orjson import loads
from sentry_sdk import capture_exception

from app.core import settings


class ProxyService:
    def __init__(self) -> None:
        self.cache: TTLCache = TTLCache(maxsize=1, ttl=settings.proxy.TTL)
        self.last_purchase_time: datetime | None = None

    @staticmethod
    async def get_ip() -> str | None:
        """
        Retrieves the current public IP address.

        Returns:
            The current IP address.
        """

        async with aiohttp.ClientSession() as session, session.get("http://checkip.dyndns.com/") as response:
            try:
                body = await response.text()
                response.raise_for_status()

                if match := re.compile(r"Address: (\d+\.\d+\.\d+\.\d+)").search(body):
                    return match.group(1)

            except ClientResponseError as e:
                capture_exception(e)
                logger.error(f"ClientResponseError: {response.status} - {body}")

            except Exception as e:
                capture_exception(e)
                logger.error(f"Error: {e}")

    async def get_balance(self) -> float:
        """
        Retrieves the current balance from the proxy provider.

        Returns:
            The current balance.

        Raises:
            Exception: If the balance could not be retrieved.
        """
        data = await self._request("GET", "balance/get")
        balance = data.get("summ")
        if balance is None:
            raise Exception("Failed to retrieve balance")
        return balance

    async def get_proxies(self) -> list[dict]:
        """
        Retrieves a list of proxies from the cache, or fetches new proxies if necessary.

        Returns:
            A list of proxies with server, username, and password details.
        """
        try:
            items = self.cache.get("proxies")
            if not items:
                proxies_list = await self.get_proxies_list(proxy_type="ipv4")
                items = proxies_list.get("items", [])
                needed = settings.proxy.NUMBER_OF_PROXIES - len(items)

                if needed > 0:
                    items = await self.buy_proxies(needed)

                self.cache["proxies"] = items

        except Exception:
            return []

        return [
            {
                "server": f"http://{item['ip']}:{item['port_http']}",
                "username": item["login"],
                "password": item["password"],
            }
            for item in items
        ]

    async def get_proxies_list(self, proxy_type: str = "") -> dict[str, Any]:
        """
        Retrieves a list of available proxies of the specified type.

        Args:
            proxy_type: The type of proxies to retrieve.

        Returns:
            The list of proxies or an empty dictionary if none are available.
        """
        endpoint = f"proxy/list/{proxy_type}" if proxy_type else "proxy/list"

        return await self._request("GET", endpoint)

    async def buy_proxies(self, quantity: int) -> list:
        """
        Attempts to purchase a specified number of proxies, throttled to avoid frequent purchases.

        Args:
            quantity: The number of proxies to purchase.

        Returns:
            A list of acquired proxies

        Raises:
            Exception: If the purchase is throttled or fails after multiple attempts.
        """
        if self.last_purchase_time and datetime.now(UTC) - self.last_purchase_time < timedelta(hours=1):
            raise Exception("Not enough time to buy")

        logger.info(f"Buying {quantity} proxies")

        ip = await self.get_ip()
        if not ip:
            raise Exception("Failed to get IP address")

        await self.buy_proxy(ip, quantity)

        attempts = 1
        while attempts <= settings.proxy.MAX_ATTEMPTS:
            proxies_list = await self.get_proxies_list(proxy_type="ipv4")
            items = proxies_list.get("items")

            if items:
                logger.info(f"Proxies acquired after {attempts} attempts.")
                self.last_purchase_time = datetime.now(UTC)
                return items

            logger.info(f"Proxy wasn't added. Waiting 10 seconds. Attempt: {attempts}/{settings.proxy.MAX_ATTEMPTS}")
            attempts += 1

            await asyncio.sleep(10)

        balance = await self.get_balance()
        raise Exception(f"Failed to acquire proxies after {settings.proxy.MAX_ATTEMPTS} attempts. Balance: {balance}")

    async def buy_proxy(self, public_ip: str, quantity: int) -> None:
        """
        Sends a request to purchase a single proxy for the given public IP.

        Args:
            public_ip: The public IP to associate with the proxy purchase.
            quantity: The number of proxies to purchase.
        """
        data = {
            "paymentId": 1,
            "generateAuth": "N",
            "countryId": settings.proxy.COUNTRY_ID,
            "periodId": settings.proxy.PERIOD_ID,
            "quantity": quantity,
            "authorization": public_ip,
            "coupon": "",
            "customTargetName": "[NDA] - For Web scraping",
        }
        await self._request("POST", "order/make", json=data)

    @staticmethod
    async def _request(method: str, uri: str, **kwargs: Any) -> dict:
        """
        Sends an HTTP request to the proxy provider's API.

        Args:
            method: The HTTP method (e.g., "GET", "POST").
            uri: The URI endpoint to send the request to.

        Raises:
            ValueError: If the API returns an error message.
            ClientResponseError: If the API returns an unexpected response.

        Returns:
            The response data from the API.
        """
        proxy = settings.proxy.base_url + uri

        async with aiohttp.ClientSession() as session, session.request(method, proxy, **kwargs) as response:
            try:
                body = await response.text()
                response.raise_for_status()
                data = loads(body)

                if data.get("status") == "success":
                    return data["data"]

                elif errors := data.get("errors"):
                    raise ValueError(errors[0]["message"])

                else:
                    raise ClientResponseError

            except ClientResponseError as e:
                logger.error(f"ClientResponseError: {response.status} - {body}")
                capture_exception(e)
                return {}

            except Exception as e:
                logger.error(f"Error: {e}")
                capture_exception(e)
                return {}


proxy_service: ProxyService = ProxyService()
