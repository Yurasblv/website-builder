from enum import StrEnum


class ProviderTypes(StrEnum):
    HETZNER = "hetzner"
    SCALEWAY = "scaleway"


class HetznerServerStatus(StrEnum):
    DELETING = "deleting"
    INITIALIZING = "initializing"
    MIGRATING = "migrating"
    OFF = "OFF"
    REBUILDING = "rebuilding"
    RUNNING = "running"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"


class ScalewayServerState(StrEnum):
    LOCKED = "locked"
    RUNNING = "running"
    STARTING = "starting"
    STOPPED = "stopped"
    STOPPED_IN_PLACE = "stopped in place"
    STOPPING = "stopping"


class ScalewayZone(StrEnum):
    FR_PAR_1 = "fr-par-1"
    FR_PAR_2 = "fr-par-2"
    FR_PAR_3 = "fr-par-3"
    NL_AMS_1 = "nl-ams-1"
    NL_AMS_2 = "nl-ams-2"
    NL_AMS_3 = "nl-ams-3"
    PL_WAW_1 = "pl-waw-1"
    PL_WAW_2 = "pl-waw-2"
    PL_WAW_3 = "pl-waw-3"
