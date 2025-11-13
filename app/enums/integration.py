from .base import BaseStrEnum


class IntegrationType(BaseStrEnum):
    integration = "integration"
    WORDPRESS = "WORDPRESS"


class WPPluginStyle(BaseStrEnum):
    WP = "wp"
    NDA = "nda"


class WPPageType(BaseStrEnum):
    PAGE = "page"
    ARTICLE = "article"


class WPIntegrationType(BaseStrEnum):
    CUSTOMER = "customer"
    PBN = "pbn"


class WPEndpoint(BaseStrEnum):
    LIMIT = "/chunk-size"
    PBN_CONTENT = "/content/{type}"
    PBN_NAME = "/name"
    PING = "/ping"
    PROCESS_BATCH = "/process-batch"
    UPLOAD = "/upload"
    UPLOAD_READY = "/ready"
    VERSION = "/version"
