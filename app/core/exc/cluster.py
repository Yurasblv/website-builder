from fastapi import status

from app.core.exc.base import BaseHTTPException, BaseWebSocketException
from app.enums import ExceptionAlias

# HTTP exceptions


class ClusterAlreadyGeneratedException(BaseHTTPException):
    status_code = status.HTTP_409_CONFLICT
    message_pattern = ("Declined. Cluster with id = '{0}' was already generated", "cluster_id")
    _exception_alias = ExceptionAlias.ClusterAlreadyGenerated


class ClusterIsNotAllowToBuildException(BaseHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    message_pattern = ("Cluster with id = '{0}' is not allowed to build. Current status: {1}", "cluster_id", "status")
    _exception_alias = ExceptionAlias.ClusterIsNotAllowToBuild


class ClusterIsNotAllowToGenerateException(BaseHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    message_pattern = (
        "Cluster with id = '{0}' is not allowed to generate. Current status: {1}",
        "cluster_id",
        "status",
    )
    _exception_alias = ExceptionAlias.ClusterIsNotAllowToGenerate


class ClusterIsNotAllowToUpdateException(BaseHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    message_pattern = (
        "Cluster with id = '{0}' is not allowed to update. Current status: {1}",
        "cluster_id",
        "status",
    )
    _exception_alias = ExceptionAlias.ClusterIsNotAllowToUpdate


class ClusterSettingUpdateException(BaseHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    message_pattern = (
        "Cluster setting for intent = '{0}' is not allowed to update. Info: {1}",
        "intent",
        "info",
    )
    _exception_alias = ExceptionAlias.ClusterIsNotAllowToUpdate


class ClusterPageUpdateException(BaseHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    _exception_alias = ExceptionAlias.ClusterPageIsNotAllowToUpdate


class ClusterPageTopicsUpdateException(BaseHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    _exception_alias = ExceptionAlias.ClusterTopicsAreNotAllowedToUpdate


class ClusterVersionUpgradeException(BaseHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    message_pattern = ("Cluster is not built, details: {0}", "details")
    _exception_alias = ExceptionAlias.ClusterVersionUpgradeIsNotAllowed


class ClusterPageVersionUpgradeException(BaseHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    message_pattern = ("ClusterPage is not built, details: {0}", "details")
    _exception_alias = ExceptionAlias.ClusterPageVersionUpgradeIsNotAllowed


class ClusterVersionDowngradeException(BaseHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    message_pattern = ("Cluster is not built, details: {0}", "details")
    _exception_alias = ExceptionAlias.ClusterVersionDowngradeIsNotAllowed


class ClusterPageVersionDowngradeException(BaseHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    message_pattern = ("ClusterPage is not built, details: {0}", "details")
    _exception_alias = ExceptionAlias.ClusterPageVersionDowngradeIsNotAllowed


class ScreenshotCreatorException(BaseHTTPException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    _exception_alias = ExceptionAlias.ScreenshotCreator


class IndustryNotFoundException(BaseHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    message_pattern = ("Industry '{0}' not found. Existing industries: {1}", "industry", "industries")
    _exception_alias = ExceptionAlias.IndustryNotFound


class ClusterStructureCreateError(BaseHTTPException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message_pattern = ("Cluster structure was not defined due to error.",)
    _exception_alias = ExceptionAlias.ClusterCreationFailed


class NotEnoughBalanceForGeneration(BaseHTTPException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    message_pattern = (
        "Not enough balance for generation. Required: {0}, available: {1} for generating {2} pages.",
        "required_amount",
        "available_amount",
        "pages_number",
    )
    _exception_alias = ExceptionAlias.NotEnoughBalanceForGeneration


# WebSocket exceptions


class ClusterIsGeneratingException(BaseWebSocketException):
    message_pattern = ("Declined. Cluster with id = '{0}' is generating", "cluster_id")
    _exception_alias = ExceptionAlias.ClusterIsGenerating


class ClusterWithoutPagesException(BaseWebSocketException):
    message_pattern = ("Declined. Cluster with id = '{0}' without pages. ", "cluster_id")
    _exception_alias = ExceptionAlias.ClusterWithoutPages
    sentry_record = True


class ClusterPagesGenerationException(BaseWebSocketException):
    message_pattern = ("Declined. Cluster with id = '{0}' generated empty pages. ", "cluster_id")
    _exception_alias = ExceptionAlias.ClusterPagesGeneratedEmpty
    sentry_record = True


class ClusterPagesGenerationFailedException(BaseWebSocketException):
    message_pattern = (
        "Declined. Cluster with id = '{0}' doesn't generate image for Page with id = '{1}'. ",
        "cluster_id",
        "page_id",
    )
    _exception_alias = ExceptionAlias.ClusterPagesGeneratedEmpty
    sentry_record = True


class GenerateUndefinedErrorException(BaseWebSocketException):
    """
    A error occurs when the connection started on the origin web server, but that the request was not completed.
    The most common reason why this would occur is that either a program, cron job,
    or resource is taking up more resources than it should causing the server not to be able
    to respond to all requests properly.
    """

    message_pattern = (
        "Unknown error. Generation of id = '{0}' with {1} pages failed.",
        "cluster_id",
        "pages_number",
    )
    _exception_alias = ExceptionAlias.UndefinedError
    sentry_record = True


class InvalidKeywordException(BaseHTTPException):
    log_level = "warning"
    message_pattern = ("Invalid keyword {0}", "keyword")
    _exception_alias = ExceptionAlias.InvalidKeyword


class MindmapFileValidationException(BaseWebSocketException):
    log_level = "warning"
    message_pattern = ("The uploaded file contains not valid main topic, topic = {0}.", "topic")
    _exception_alias = ExceptionAlias.MindmapFileUploadFailed


class MindmapFileUploadException(BaseHTTPException):
    log_level = "warning"
    message_pattern = ("The uploaded file is not a valid {0} file.", "expected_file_type")
    _exception_alias = ExceptionAlias.MindmapFileUploadFailed


class MindmapPageCountMismatchException(BaseHTTPException):
    log_level = "warning"
    message_pattern = ("Mindmap page count does not match the expected value.",)
    _exception_alias = ExceptionAlias.MindmapPageCountMismatch
