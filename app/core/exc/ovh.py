from app.core.exc import BaseHTTPException
from app.enums import ExceptionAlias


class OVHMaxRetryException(Exception):
    """Raised when the maximum number of retries is reached"""

    def __init__(self, message: str = "Max retries reached. Upload failed.") -> None:
        self.message = message
        super().__init__(self.message)


class OVHFailedFetchFileException(BaseHTTPException):
    message_pattern = ("Failed to fetch the file",)
    log_message_pattern = ("Failed to fetch the file, error={0}", "error")
    _exception_alias = ExceptionAlias.FailedFetchFile
