from fastapi import status

from app.core.exc.base import BaseHTTPException
from app.enums import ExceptionAlias


class DomainNotAvailable(BaseHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    message_pattern = ("The domain {0} is not available for registration.", "name")
    _exception_alias = ExceptionAlias.DomainNotAvailable


class DomainsNotAvailable(BaseHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    message_pattern = ("The domains {0} are not available for registration.", "names")
    _exception_alias = ExceptionAlias.DomainsNotAvailable


class DomainDNSCheckerServiceUnavailable(BaseHTTPException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message_pattern = ("The domain DNS checker service is unavailable.",)
    _exception_alias = ExceptionAlias.DomainDNSCheckerServiceUnavailable


class DomainCustomIsNotConfirmed(BaseHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    message_pattern = (
        "The domain {0} is not confirmed. Expected NS: {1}. Existing NS: {2}",
        "domain",
        "expected_ns",
        "existing_ns",
    )
    _exception_alias = ExceptionAlias.DomainCustomIsNotConfirmed
