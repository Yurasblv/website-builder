from app.enums.base import BaseStrEnum

from .hetzner import HetznerImageType, HetznerLocationType, HetznerServerType
from .scaleway import ScalewayImageType, ScalewayLocationType, ScalewayServerType


class ServerProviderEndpoint(BaseStrEnum):
    # Management endpoints
    CREATE = "providers/{provider_type}/{location}"
    GET = "providers/{provider_type}/{location}/{server_id}"
    DELETE = "providers/{provider_type}/{location}/{server_id}"
    STATUS = "providers/{provider_type}/{location}/{server_id}/status"
    DNS = "providers/{provider_type}/{location}/{server_id}/dns"

    # Script endpoints
    SCRIPT_SETUP = "scripts/setup"
    SCRIPT_WORDPRESS = "scripts/wordpress"


class ServerProviderType(BaseStrEnum):
    HETZNER = "hetzner"  # currently used shared vcpu for amd
    SCALEWAY = "scaleway"

    @property
    def locations(self) -> list[str]:
        match self:
            case ServerProviderType.HETZNER:
                return [i.value for i in HetznerLocationType.list()]

            case ServerProviderType.SCALEWAY:
                return [i.value for i in ScalewayLocationType.list()]

            case _:
                return []

    @property
    def server_type(self) -> str:
        match self:
            case ServerProviderType.HETZNER:
                return HetznerServerType.CPX11

            case ServerProviderType.SCALEWAY:
                return ScalewayServerType.DEV1_S

            case _:
                return ""

    @property
    def image(self) -> str:
        match self:
            case ServerProviderType.HETZNER:
                return HetznerImageType.UBUNTU_20_04

            case ServerProviderType.SCALEWAY:
                return ScalewayImageType.UBUNTU_FOCAL

            case _:
                return ""

    @classmethod
    def combinations(cls) -> list[dict]:
        return [
            {
                "provider_type": provider_type,  # TODO: return service class based on provider type
                "location": location,
                "image": provider_type.image,
                "server_type": provider_type.server_type,
            }
            for provider_type in cls
            if provider_type == ServerProviderType.HETZNER  # TODO: remove after scaleway completion
            for location in provider_type.locations
        ]


class ServerProviderStatus(BaseStrEnum):
    RUNNING = "running"
    STARTING = "starting"
    STOPPING = "stopping"
    STOPPED = "stopped"
    PROCESSING = "processing"
    UNKNOWN = "unknown"
