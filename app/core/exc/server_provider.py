from fastapi import status

from app.core.exc.base import BaseHTTPException
from app.enums import ExceptionAlias


class ServerNotAvailable(BaseHTTPException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message_pattern = ("The server {0} is not available for using. Server status {1}", "name", "status")
    _exception_alias = ExceptionAlias.ServerNotAvailable
