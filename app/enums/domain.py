from enum import StrEnum

from app.enums.base import BaseStrEnum


class DomainType(BaseStrEnum):
    """
    Domain types.

    EXPIRED: Expired domain type
    CUSTOM: Custom domain type
    AI_GENERATED: AI domain type
    """

    EXPIRED = "EXPIRED"
    CUSTOM = "CUSTOM"
    AI_GENERATED = "AI_GENERATED"


class DomainStatus(BaseStrEnum):
    """
    Domain statuses.

    NEW: The domain is newly created and not yet processed.
    READY: The domain is ready to use.
    PROCESSING: The domain setup is processing.
    WAITING_FOR_APPROVAL: The domain is awaiting approval for activation.
    FAILED: The domain setup has failed.
    """

    NEW = "NEW"
    READY = "READY"
    PROCESSING = "PROCESSING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    FAILED = "FAILED"


class SubRecordType(StrEnum):
    CNAME = "cname"
    TXT = "txt"


class DynadotCommand(StrEnum):
    BALANCE = "get_account_balance"
    CONTACT_LIST = "contact_list"
    GET_NS = "get_ns"
    ORDER_STATUS = "get_order_status"
    REGISTER = "register"
    SEARCH = "search"
    SET_DNS2 = "set_dns2"
    SET_NS = "set_ns"
