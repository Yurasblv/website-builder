from .abc import AbstractStorageRepository
from .local import LocalStorageRepository
from .local import repository as local_storage
from .s3 import S3StorageRepository
from .s3 import repository as s3_storage

ovh_service: LocalStorageRepository | S3StorageRepository = local_storage or s3_storage
storage: LocalStorageRepository | S3StorageRepository = local_storage or s3_storage

__all__ = (
    "S3StorageRepository",
    "LocalStorageRepository",
    "AbstractStorageRepository",
    "ovh_service",
    "storage",
)
