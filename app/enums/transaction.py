from app.enums.base import BaseStrEnum


class TransactionStatus(BaseStrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SpendType(BaseStrEnum):
    CLUSTER_PAGES = "cluster_pages"
    CTR_CAMPAIGN = "ctr_campaign"
    PBN = "pbn"
    EXTRA_PBN_PAGE = "extra_pbn_page"
    DOMAIN_AI = "domain_ai"
    DOMAIN_EXPIRED = "domain_expired"
    REFRESH_CLUSTER = "refresh_cluster"
    REFRESH_CLUSTER_PAGE = "refresh_cluster_page"
    REFRESH_PBN = "refresh_pbn"


class DepositMethod(BaseStrEnum):
    STRIPE = "stripe"
    CRYPTO = "crypto"


class WithdrawMethod(BaseStrEnum):
    BANK = "bank"
    CRYPTO = "crypto"


class TransferMethod(BaseStrEnum):
    SWIFT = "SWIFT"
    SEPA = "SEPA"


class TransactionType(BaseStrEnum):
    SPEND = "spend"
    DEPOSIT = "deposit"
    REFERRAL = "referral"
    WITHDRAW = "withdraw"
    BONUS = "bonus"
    REFUND = "refund"


class CryptoCurrency(BaseStrEnum):
    USDT = "USDT"


class USDTNetwork(BaseStrEnum):
    TRC20 = "TRC20"
    ERC20 = "ERC20"
    BEP20 = "BEP20"
