from app.enums.base import BaseStrEnum


class VoucherStatus(BaseStrEnum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"


class VoucherType(BaseStrEnum):
    REFERRAL = "REFERRAL"
    PROMO = "PROMO"
    REFUND = "REFUND"
    LOYALTY = "LOYALTY"


class VoucherLoyaltyProgram(BaseStrEnum):
    CASHBACK = "CASHBACK"
    WELCOME = "WELCOME"
