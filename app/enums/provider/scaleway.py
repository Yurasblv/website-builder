from app.enums.base import BaseStrEnum


class ScalewayLocationType(BaseStrEnum):
    PARIS_1 = "fr-par-1"
    PARIS_2 = "fr-par-2"
    PARIS_3 = "fr-par-3"
    AMSTERDAM_1 = "nl-ams-1"
    AMSTERDAM_2 = "nl-ams-2"
    AMSTERDAM_3 = "nl-ams-3"
    WARSAW_1 = "pl-waw-1"
    WARSAW_2 = "pl-waw-2"
    WARSAW_3 = "pl-waw-3"


class ScalewayServerType(BaseStrEnum):
    DEV1_S = "DEV1-S"


class ScalewayImageType(BaseStrEnum):
    UBUNTU_FOCAL = "ubuntu_focal"
