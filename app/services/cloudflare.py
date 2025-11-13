from functools import partial

from aiohttp import ClientSession
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding
from loguru import logger
from orjson import dumps, loads

from app.core import settings
from app.core.exc.cloudflare import (
    CloudflareNoAccountException,
    CloudflareZoneCreationFailedException,
    CloudFlareZoneNotFoundException,
    CloudFlareZoneNotFoundForDomainException,
)
from app.db.redis import redis_pool
from app.schemas import (
    CloudFlareAccount,
    CloudflareSSLCertificateResponse,
    CloudFlareSSLCertificateSettingsResponse,
    CloudFlareZoneResponse,
)


class CloudflareService:
    """
    Service for interacting with the Cloudflare API to manage zones, accounts, and SSL certificates.
    """

    _zones_url = f"{settings.cloudflare.BASE_URL}/zones"
    _accounts_url = f"{settings.cloudflare.BASE_URL}/accounts"
    _certificates_url = f"{settings.cloudflare.BASE_URL}/certificates"

    headers = {
        "Authorization": f"Bearer {settings.cloudflare.TOKEN}",
        "Content-Type": "application/json",
    }
    client = partial(ClientSession, headers=headers, raise_for_status=True)

    @classmethod
    async def get_account(cls) -> CloudFlareAccount:
        """
        Retrieves the first account ID associated with the API token.

        Returns:
            An object containing account details.

        Raises:
            CloudflareNoAccountException: If the API request fails.
        """

        async with cls.client() as session, session.get(cls._accounts_url) as response:
            data = await response.json()

        if not (result := data.get("result")):
            raise CloudflareNoAccountException()

        return CloudFlareAccount.model_validate(result[0])

    @classmethod
    async def create_zone(cls, domain: str) -> CloudFlareZoneResponse:
        """
        Creates a new zone in Cloudflare under the specified account.

        Args:
            domain: The domain name to associate with the zone.

        Returns:
            A dictionary containing details about the newly created zone.

        Raises:
            Exception: If the API request fails.
        """

        account = await cls.get_account()

        payload = {"name": domain, "account": {"id": account.id}, "type": "full"}

        async with cls.client() as session, session.post(cls._zones_url, json=payload) as response:
            data = await response.json()

        try:
            response = CloudFlareZoneResponse.model_validate(data)
            # If the Universal SSL certificate setting is not enabled, create an Origin SSL certificate
            if not await cls.is_universal_ssl_cert_enabled(response.result.id):
                await cls.generate_ssl_cert(domain)

            await cls._cache_zone_ssl_cert(response.result.id, domain)

            return response

        except Exception:
            raise CloudflareZoneCreationFailedException(domain=domain)

    @classmethod
    async def add_a_record(cls, domain_name: str, ip: str) -> None:
        """
        Updates DNS records for the given domain in Cloudflare.

        Args:
            domain_name: The domain name to update DNS records for.
            ip: The IP address to set for the A record.
        """

        payload = {
            "name": domain_name,
            "type": "A",
            "content": ip,
            "ttl": 3600,
            "proxied": False,
        }

        async with cls.client() as session:
            url_zone_list = f"{cls._zones_url}?name={domain_name}"

            async with session.get(url_zone_list) as zone_list_response:
                zone_list_data = await zone_list_response.json()
                zone_list_result = zone_list_data.get("result")

                if not zone_list_result:
                    raise CloudFlareZoneNotFoundForDomainException(domain=domain_name)

            zone_id = zone_list_result[0].get("id")
            url_dns_records = f"{cls._zones_url}/{zone_id}/dns_records"

            async with session.post(url_dns_records, json=payload) as dns_records_response:
                dns_records_data = await dns_records_response.json()
                logger.debug(f"DNS A record added: {dns_records_data}")

    @classmethod
    async def delete_a_record(cls, domain_name: str) -> None:
        """
        Updates DNS records for the given domain in Cloudflare.

        Args:
            domain_name: The domain name to update DNS records for.
        """

        async with cls.client() as session:
            url_zone_list = f"{cls._zones_url}?name={domain_name}"

            async with session.get(url_zone_list) as zone_list_response:
                zones_list = await zone_list_response.json()
                result = zones_list.get("result", [])

            if not result:
                return

            zone_id = result[0].get("id")
            url_dns_records = f"{cls._zones_url}/{zone_id}/dns_records"

            async with session.get(url_dns_records) as dns_records_response:
                dns_records = await dns_records_response.json()
                a_records = dns_records.get("result", [])

            for record in a_records:
                if record_id := record.get("id", None):
                    async with session.delete(url_dns_records + f"/{record_id}") as _:
                        logger.debug(f"DNS A record removing: {record_id}")

    @classmethod
    async def get_zone_details(cls, zone_id: str) -> CloudFlareZoneResponse:
        """
        Retrieves details about a specific zone in Cloudflare.

        Args:
            zone_id: The ID of the Cloudflare zone.

        Returns:
            A dictionary containing details about the specified zone.

        Raises:
            CloudFlareZoneNotFoundException: If no result is returned for the zone.
        """

        url = f"{cls._zones_url}/{zone_id}"

        async with cls.client() as session, session.get(url) as response:
            data = await response.json()

        if not data.get("result"):
            raise CloudFlareZoneNotFoundException(zone_id=zone_id)

        return CloudFlareZoneResponse.model_validate(data)

    @staticmethod
    async def _cache_zone_ssl_cert(zone_id: str, domain: str) -> None:
        """
        Cache SSL certificate metadata for the given domain in Redis.

        Args:
            zone_id: ID of the Cloudflare zone.
            domain: Domain name for SSL cert.
        """

        redis = await redis_pool.get_redis()
        ssl_cert_key = settings.cloudflare.redis_key.format(domain)

        if not await redis.get(ssl_cert_key):
            cert_info = dumps({"zone_id": zone_id, "domain": domain})
            await redis.set(name=ssl_cert_key, value=cert_info)

    @classmethod
    async def delete_zone(cls, zone_id: str) -> bool:
        """
        Deletes a zone in Cloudflare.

        Args:
            zone_id: The ID of the Cloudflare zone to delete.

        Returns:
            True if the zone was successfully deleted, False otherwise.
        """

        url = f"{cls._zones_url}/{zone_id}"

        async with cls.client() as session, session.delete(url) as response:
            data = await response.json()

        response = CloudFlareZoneResponse.model_validate(data)

        return response.success

    @staticmethod
    def _generate_cert_request() -> str:
        """
        Generate a PEM-encoded certificate signing request (CSR).

        Returns:
            CSR as a PEM-formatted string.
        """

        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        subject = x509.Name(
            [
                x509.NameAttribute(x509.oid.NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(x509.oid.NameOID.STATE_OR_PROVINCE_NAME, "California"),
                x509.NameAttribute(x509.oid.NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(x509.oid.NameOID.ORGANIZATION_NAME, "My Company"),
                x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, "example.net"),
            ]
        )

        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(subject)
            .sign(private_key=key, algorithm=hashes.SHA256())
        )

        return csr.public_bytes(Encoding.PEM).decode()

    @classmethod
    async def generate_ssl_cert(cls, domain: str) -> None:
        """
        Creates an origin SSL certificate for a given domain in Cloudflare.

        Args:
            domain: The domain for which the SSL certificate is requested.
        """

        payload = {
            "csr": cls._generate_cert_request(),
            "hostnames": [domain],
            "request_type": "origin-rsa",
            "requested_validity": 5475,  # 15 years
        }

        async with cls.client() as session, session.post(cls._certificates_url, json=payload):
            ...

    @classmethod
    async def is_universal_ssl_cert_enabled(cls, zone_id: str) -> bool:
        """
        Checks if Universal SSL is enabled for a given zone.

        Args:
            zone_id: The ID of the Cloudflare zone.

        Raises:
            CloudFlareZoneNotFoundException: If no result is returned for the zone.

        Returns:
            True if Universal SSL is enabled, False otherwise.
        """

        url = f"{cls._zones_url}/{zone_id}/ssl/universal/settings"

        async with cls.client() as session, session.get(url) as response:
            data = await response.json()

        if not data.get("result"):
            raise CloudFlareZoneNotFoundException(zone_id=zone_id)

        response = CloudFlareSSLCertificateSettingsResponse.model_validate(data)

        return response.result.enabled

    @classmethod
    async def check_ssl_cert_availability(cls, zone_id: str) -> bool:
        """
        Checks if SSL certificate packs are available for a specific zone.

        Args:
            zone_id: The ID of the Cloudflare zone.

        Returns:
            True if SSL certificates are available, False otherwise.
        """

        is_cert_enabled = await cls.is_universal_ssl_cert_enabled(zone_id)

        url = (
            f"{cls._zones_url}/{zone_id}/ssl/certificate_packs"
            if is_cert_enabled
            else f"{cls._certificates_url}?zone_id={zone_id}"
        )

        async with cls.client() as session, session.get(url) as response:
            data = loads(await response.text())

        response = CloudflareSSLCertificateResponse.model_validate(data)

        return bool(response.result)
