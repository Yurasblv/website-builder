from app.enums.base import BaseStrEnum


class HetznerLocationType(BaseStrEnum):
    # germany
    FALKENSTEIN = "fsn1"
    NUREMBERG = "nbg1"

    # finland
    HELSINKI = "hel1"

    # usa
    ASHBURN = "ash"
    HILLSBORO = "hil"


class HetznerServerType(BaseStrEnum):
    CPX11 = "cpx11"


class HetznerImageType(BaseStrEnum):
    UBUNTU_20_04 = "ubuntu-20.04"
