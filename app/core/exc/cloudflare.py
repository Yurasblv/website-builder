from fastapi import status

from app.core.exc.base import BaseHTTPException, BaseWebSocketException
from app.enums import ExceptionAlias


class CloudFlareZoneNotFoundException(BaseHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    message_pattern = ("No available zone found for zone_id = '{0}'", "zone_id")
    _exception_alias = ExceptionAlias.CloudFlareNoAvailableZone


class CloudFlareZoneNotFoundForDomainException(BaseHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    message_pattern = ("No available zone found for domain = '{0}'", "domain")
    _exception_alias = ExceptionAlias.CloudFlareNoAvailableZone


class CloudflareNoAccountException(BaseHTTPException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message_pattern = ("No Cloudflare account available",)
    _exception_alias = ExceptionAlias.CloudflareNoAccount


class CloudflareZoneCreationFailedException(BaseHTTPException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message_pattern = ("Unable to create zone for domain = '{0}'", "domain")
    _exception_alias = ExceptionAlias.CloudFlareZoneCreationFailed


class CloudflareARecordCreationException(BaseWebSocketException):
    message_pattern = ("Unable to create A record for domain = '{0}'. Exc = '{1}'. ", "domain", "exc")
    _exception_alias = ExceptionAlias.CloudFlareARecordCreationFailed
    sentry_record = True
