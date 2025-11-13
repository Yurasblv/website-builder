from fastapi import status

from app.core.exc.base import BaseHTTPException
from app.enums import ExceptionAlias


class PermissionDeniedException(BaseHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    message_pattern = ("You can't perform this action",)
    _exception_alias = ExceptionAlias.PermissionDenied


class InvalidTokenException(BaseHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    message_pattern = ("Invalid token signature. {0}", "error")
    _exception_alias = ExceptionAlias.InvalidToken
