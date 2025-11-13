from fastapi import status

from app.core.exc import BaseHTTPException
from app.enums import ExceptionAlias


class IntegrationWPAlreadyExistsException(BaseHTTPException):
    """
    Exception raised when a WordPress integration already exists.
    """

    status_code = status.HTTP_409_CONFLICT
    message_pattern = ("WordPress integration already exists",)
    _exception_alias = ExceptionAlias.WPAlreadyExists


class IntegrationWPConnectionException(BaseHTTPException):
    """
    Exception raised when a connection to the WordPress plugin fails.
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message_pattern = (
        "Failed to connect to WordPress plugin at {0}. Status code: {1}, Response: {2}",
        "url",
        "status_code",
        "response_text",
    )
    _exception_alias = ExceptionAlias.WPBadConnection


class IntegrationWPDomainNotFoundException(BaseHTTPException):
    """
    Exception raised when a domain is not found.
    """

    status_code = status.HTTP_404_NOT_FOUND
    message_pattern = ("URL {0} not found", "url")
    _exception_alias = ExceptionAlias.WPDomainNotFound


class IntegrationWPInvalidAPIKeyException(BaseHTTPException):
    """
    Exception raised when a WordPress API key is invalid.
    """

    status_code = status.HTTP_403_FORBIDDEN
    message_pattern = ("Permission denied. API key is invalid for URL {0}", "url")
    _exception_alias = ExceptionAlias.WPInvalidAPIKey


class IntegrationWPWrongPluginUrl(BaseHTTPException):
    """
    Exception raised when a WordPress plugin url is wrong.
    """

    status_code = status.HTTP_404_NOT_FOUND
    message_pattern = ("Wrong plugin URL {0}. Status code {1}", "url", "status_code")
    _exception_alias = ExceptionAlias.WPWrongPluginUrl


class IntegrationWPStillInProgressException(BaseHTTPException):
    """
    Exception raised when a WordPress integration is still in progress.
    """

    status_code = status.HTTP_409_CONFLICT
    message_pattern = ("Domain {0} is still in progress", "domain")
    _exception_alias = ExceptionAlias.WPStillInProgress


class IntegrationWPIsNotLatestVersionException(BaseHTTPException):
    """
    Exception raised when a WordPress integration is not the latest version.
    """

    status_code = status.HTTP_409_CONFLICT
    message_pattern = (
        "Domain {0} is not the latest version. Current version: {1}. Latest version: {2}",
        "domain",
        "current_version",
        "latest_version",
    )
    _exception_alias = ExceptionAlias.WPIsNotLatestVersion
