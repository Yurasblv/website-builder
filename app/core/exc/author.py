from fastapi import status

from app.core.exc.base import BaseHTTPException
from app.enums import ExceptionAlias


class RestrictedAuthorDeleting(BaseHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    message_pattern = ("You can't delete the author because it has related posts.",)
    _exception_alias = ExceptionAlias.RestrictedAuthorDeleting


class AuthorSocialNetworkExistsException(BaseHTTPException):
    status_code = status.HTTP_409_CONFLICT
    message_pattern = ("Declined. Social network {0} for author {1} exists", "social_network_type", "author_id")
    _exception_alias = ExceptionAlias.AuthorSocialNetworkExists


class AuthorAvatarAlreadyExists(BaseHTTPException):
    status_code = status.HTTP_409_CONFLICT
    message_pattern = ("Avatar for author {0} already exists", "author_id")
    _exception_alias = ExceptionAlias.AuthorAvatarAlreadyExists


class AuthorAvatarDoesNotExist(BaseHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    message_pattern = ("Avatar for author {0} does not exist", "author_id")
    _exception_alias = ExceptionAlias.AuthorAvatarDoesNotExist
