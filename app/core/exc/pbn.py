from fastapi import status

from app.core.exc.base import BaseHTTPException, BaseWebSocketException
from app.enums import ExceptionAlias

# HTTP exceptions


class PBNExtraPageAlreadyGeneratedException(BaseHTTPException):
    status_code = status.HTTP_409_CONFLICT
    message_pattern = ("Declined. PBN with id = '{0}' was already generated", "pbn_id")
    _exception_alias = ExceptionAlias.PBNExtraPageAlreadyGenerated


class PBNExtraPageIsNotAllowToBuildException(BaseHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    message_pattern = ("Blog with id = '{0}' is not allowed to build. Current status: {1}", "pbn_id", "status")
    _exception_alias = ExceptionAlias.PBNExtraPageIsNotAllowToBuild


class PBNExtraPageTitleException(BaseHTTPException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message_pattern = ("Error during title creation",)
    _exception_alias = ExceptionAlias.PBNExtraPageIsNotAllowToBuild


class PBNExtraPageIsNotAllowToGenerateException(BaseHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    message_pattern = (
        "PBN id = '{0}' is not allowed to generate extra page. Current status: {1}",
        "pbn_id",
        "status",
    )
    _exception_alias = ExceptionAlias.PBNExtraPageIsNotAllowToGenerate


class PbnDomainsCheckException(BaseHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    message_pattern = ("Domains were not found",)
    _exception_alias = ExceptionAlias.PBNIsGenerating


class PBNExtraPageIsGeneratingException(BaseHTTPException):
    sentry_record = status.HTTP_429_TOO_MANY_REQUESTS
    message_pattern = ("Declined. PBN with id = '{0}' is generating", "pbn_id")
    _exception_alias = ExceptionAlias.PBNIsGenerating


class MoneysiteIsProcessingException(BaseHTTPException):
    sentry_record = status.HTTP_429_TOO_MANY_REQUESTS
    message_pattern = ("Declined. Money site = '{0}' for user = '{1}' is processing", "moneysite_url", "user_id")
    _exception_alias = ExceptionAlias.MoneysiteProcessing


class PBNPageTemplateException(BaseHTTPException):
    sentry_record = status.HTTP_403_FORBIDDEN
    message_pattern = ("Template render for {0} type failed. ", "page_type")
    _exception_alias = ExceptionAlias.PBNHomePageTemplateRenderError


class MoneysiteRequestException(BaseHTTPException):
    sentry_record = status.HTTP_500_INTERNAL_SERVER_ERROR
    message_pattern = ("Request to generate pbns for moneysite '{0}' failed.", "moneysite_url")
    _exception_alias = ExceptionAlias.MoneysiteRequestError


class PBNPlanStructureException(BaseHTTPException):
    sentry_record = status.HTTP_500_INTERNAL_SERVER_ERROR
    message_pattern = ("Structure render for {0} plan failed. ", "plan_id")
    _exception_alias = ExceptionAlias.PBNPlanStructureRenderError


class PBNExtraPageAuthorIsNotDefined(BaseHTTPException):
    sentry_record = status.HTTP_404_NOT_FOUND
    message_pattern = (
        "Cannot define an author for user with id = '{0}' and industry_id = '{1}'. ",
        "user_id",
        "industry_id",
    )
    _exception_alias = ExceptionAlias.PBNExtraPageAuthorIsNotDefined


class PBNNotEnoughBalanceForGeneration(BaseHTTPException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    message_pattern = (
        "Not enough balance for PBN generation. Required: {0}, available: {1} for generating {2} pages",
        "required",
        "available",
        "pages_number",
    )
    _exception_alias = ExceptionAlias.NotEnoughBalanceForGeneration


class PBNBuildingException(BaseHTTPException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message_pattern = ("Building of pbn {0} failed.", "pbn_id")
    _exception_alias = ExceptionAlias.PBNBuildError


class PBNIsRefreshingException(BaseHTTPException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    message_pattern = ("PBN's refresh is already in progress for user = '{0}'.", "user_id")
    _exception_alias = ExceptionAlias.PBNIsRefreshing


class PBNRefreshException(BaseHTTPException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message_pattern = ("Refresh pbn error.",)
    _exception_alias = ExceptionAlias.PBNUnableToRefresh


# WebSocket exceptions


class PBNExtraPageGenerationException(BaseWebSocketException):
    message_pattern = (
        "Error during extra pbn page generation. PBN = {0}. Info: {1}.",
        "pbn_id",
        "info",
    )
    _exception_alias = ExceptionAlias.PBNExtraPageGeneratedError
