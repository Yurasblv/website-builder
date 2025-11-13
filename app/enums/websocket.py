from app.enums.base import BaseStrEnum


class ClusterEventEnum(BaseStrEnum):
    ALL = "cluster.all"
    ALL_COMMUNITY = "cluster.all.community"
    ALL_DRAFT = "cluster.all.draft"
    All_CREATED = "cluster.all.created"
    BUILDING = "cluster.building"
    BUILT = "cluster.built"  # IMPORTANT: get pip-pong
    CREATED = "cluster.created"  # IMPORTANT: get pip-pong
    CREATING = "cluster.creating"
    DELETED = "cluster.deleted"
    GENERATED = "cluster.generated"  # IMPORTANT: get pip-pong
    GENERATING = "cluster.generating"
    STATUS_CHANGED = "cluster.status.changed"
    UPDATED = "cluster.updated"
    UPLOADED = "cluster.uploaded"  # IMPORTANT: get pip-pong
    UPLOADING = "cluster.uploading"


class CTREventEnum(BaseStrEnum):
    FAILED = "ctr.failed"
    PATTERN_BROKEN = "ctr.pattern.broken"
    PATTERN_PROCESSED = "ctr.pattern.processed"
    PATTERN_PROCESSING = "ctr.pattern.processing"
    PROCESSED = "ctr.processed"
    PROCESSING = "ctr.processing"


class WebsocketEventEnum(BaseStrEnum):
    CONNECTION = "websocket.connection"
    DISCONNECTION = "websocket.disconnection"
    ERROR = "error"  # IMPORTANT: get pip-pong


class ReleaseEventEnum(BaseStrEnum):
    NEW = "release.new"
    CURRENT = "release.current"


class QueueEventEnum(BaseStrEnum):
    CHANGED = "queue.changed"
    CURRENT = "queue.current"


class MessageEventEnum(BaseStrEnum):
    CONFIRM = "message.confirm"


class MoneySiteEventEnum(BaseStrEnum):
    GENERATING = "moneysite.generating"
    GENERATED = "moneysite.generated"


class PBNEventEnum(BaseStrEnum):
    CREATED = "pbn.created"
    GENERATING = "pbn.generating"
    GENERATED = "pbn.generated"
    BUILDING = "pbn.building"  # IMPORTANT: get pip-pong
    BUILT = "pbn.built"  # IMPORTANT: get pip-pong
    DEPLOYING = "pbn.deploying"
    DEPLOYED = "pbn.deployed"
    STATUS_CHANGED = "pbn.status.changed"
    UPDATED = "pbn.updated"


class PBNExtraPageEventEnum(BaseStrEnum):
    CREATED = "pbn.extra_page.created"
    GENERATING = "pbn.extra_page.generating"
    GENERATED = "pbn.extra_page.generated"
    BUILDING = "pbn.extra_page.building"
    BUILT = "pbn.extra_page.built"
    DEPLOYING = "pbn.extra_page.deploying"
    DEPLOYED = "pbn.extra_page.deployed"


class AllEventEnum(BaseStrEnum):
    # CLUSTER
    CLUSTER_ALL = "cluster.all"
    CLUSTER_ALL_COMMUNITY = "cluster.all.community"
    CLUSTER_ALL_DRAFT = "cluster.all.draft"
    CLUSTER_All_CREATED = "cluster.all.created"
    CLUSTER_BUILDING = "cluster.building"
    CLUSTER_BUILT = "cluster.built"  # IMPORTANT: get pip-pong
    CLUSTER_CREATED = "cluster.created"  # IMPORTANT: get pip-pong
    CLUSTER_CREATING = "cluster.creating"
    CLUSTER_DELETED = "cluster.deleted"
    CLUSTER_GENERATED = "cluster.generated"  # IMPORTANT: get pip-pong
    CLUSTER_GENERATING = "cluster.generating"
    CLUSTER_STATUS_CHANGED = "cluster.status.changed"
    CLUSTER_UPDATED = "cluster.updated"
    CLUSTER_UPLOADED = "cluster.uploaded"  # IMPORTANT: get pip-pong

    # CTR
    CTR_FAILED = "ctr.failed"
    CTR_PATTERN_BROKEN = "ctr.pattern.broken"
    CTR_PATTERN_PROCESSED = "ctr.pattern.processed"
    CTR_PATTERN_PROCESSING = "ctr.pattern.processing"
    CTR_PROCESSED = "ctr.processed"
    CTR_PROCESSING = "ctr.processing"

    # PBN
    PBN_CREATED = "pbn.created"
    PBN_GENERATING = "pbn.generating"
    PBN_GENERATED = "pbn.generated"
    PBN_BUILDING = "pbn.building"
    PBN_BUILT = "pbn.built"  # IMPORTANT: get pip-pong
    PBN_DEPLOYING = "pbn.deploying"
    PBN_DEPLOYED = "pbn.deployed"
    PBN_STATUS_CHANGED = "pbn.status.changed"

    # PBN EXTRA PAGE
    PBN_EXTRA_PAGE_GENERATING = "pbn.extra_page.generating"
    PBN_EXTRA_PAGE_GENERATED = "pbn.extra_page.generated"
    PBN_EXTRA_PAGE_BUILDING = "pbn.extra_page.building"
    PBN_EXTRA_PAGE_BUILT = "pbn.extra_page.built"
    PBN_EXTRA_PAGE_DEPLOYING = "pbn.extra_page.deploying"
    PBN_EXTRA_PAGE_DEPLOYED = "pbn.extra_page.deployed"
    PBN_EXTRA_PAGE_STATUS_CHANGED = "pbn.extra_page.status.changed"
    PBN_EXTRA_PAGE_UPDATED = "pbn.extra_page.updated"

    # MONEY SITE
    PROCESSING = "money_site.processing"
    DONE = "money_site.done"

    # DEFAULT
    CONFIRM = "message.confirm"
    ERROR = "error"  # IMPORTANT: get pip-pong
    QUEUE_CHANGED = "queue.changed"
    QUEUE_CURRENT = "queue.current"
    RELEASE_CURRENT = "release.current"
    RELEASE_NEW = "release.new"
