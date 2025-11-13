from fastapi import status

from app.core.exc.base import BaseHTTPException
from app.enums import ExceptionAlias


class NotEnoughBalanceForSpend(BaseHTTPException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    message_pattern = (
        "Not enough balance for spend. Required: {0}, available: {1}",
        "required_amount",
        "available_amount",
    )
    _exception_alias = ExceptionAlias.NotEnoughBalanceForSpend
