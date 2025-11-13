from enum import StrEnum

from app.enums.base import BaseStrEnum


class PBNGenerationStatus(BaseStrEnum):
    """
    Statuses for PBN.
    """

    DRAFT = "DRAFT"
    GENERATING = "GENERATING"
    GENERATED = "GENERATED"

    BUILDING = "BUILDING"
    BUILT = "BUILT"
    BUILD_FAILED = "BUILD_FAILED"
    REBUILDING = "REBUILDING"

    DEPLOYING = "DEPLOYING"
    DEPLOYED = "DEPLOYED"
    DEPLOY_FAILED = "DEPLOY_FAILED"
    REDEPLOYING = "REDEPLOYING"

    ERROR = "ERROR"

    # EXTRA PAGE
    EXTRA_PAGE_GENERATING = "EXTRA_PAGE_GENERATING"
    EXTRA_PAGE_BUILDING = "EXTRA_PAGE_BUILDING"
    EXTRA_PAGE_DEPLOYING = "EXTRA_PAGE_DEPLOYING"

    @classmethod
    def able_to_retry(cls) -> list[StrEnum]:
        """Statuses for starting generation of cluster"""
        return [cls.BUILD_FAILED, cls.DEPLOY_FAILED]

    @classmethod
    def able_to_restart_statuses(cls) -> list[BaseStrEnum]:
        """Statuses that allow to restart the server"""
        return [cls.DRAFT, cls.BUILD_FAILED, cls.DEPLOY_FAILED, cls.DEPLOYED, cls.ERROR]


class PBNPlanType(BaseStrEnum):
    BASIC = "BASIC"
    ADVANCED = "ADVANCED"
    PRO = "PRO"
    EXPERT = "EXPERT"


class PBNTierType(BaseStrEnum):
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"


class BacklinkPublishPeriodEnum(BaseStrEnum):
    IMMEDIATE = "immediate"
    IN_15_DAYS = "in_15_days"
