from app.enums.base import BaseStrEnum


class SOAXConnectionType(BaseStrEnum):
    MOBILE = "mobile"

    @property
    def endpoint(self) -> str:
        return getattr(SOAXEndpoints, self.name)


class SOAXEndpoints(BaseStrEnum):
    """
    Enum for SOAX API endpoints.

    CITY: Get country cities.
    MOBILE: Get mobile proxies.
    REGION: Get country regions.

    """

    CITY = "get-country-cities"
    MOBILE = "get-country-operators"
    REGION = "get-country-regions"
