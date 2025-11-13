from typing import Annotated
from urllib.parse import quote

from pydantic import UUID4, BaseModel, HttpUrl, field_validator

from app.enums.provider import ServerProviderType
from app.schemas.mixins import StrToJSONMixin


class PBNFinalizeGenerate(BaseModel):
    generation_key: str
    user_id: str
    money_site_id: str
    money_site_url: str
    tx_id: str

    @field_validator("user_id", "money_site_id", "money_site_url", "tx_id", mode="before")
    @classmethod
    def validate_fields(cls, value: UUID4 | HttpUrl) -> str:
        return str(value)


class PBNServerBase(BaseModel):
    user_id: str
    pbn_id: str

    @field_validator("user_id", "pbn_id", mode="before")
    @classmethod
    def validate_fields(cls, value: UUID4) -> str:
        return str(value)


class PBNServerStatusCheck(PBNServerBase):
    domain: str
    server_id: str
    location: str
    provider_type: ServerProviderType


class PBNServerSetup(StrToJSONMixin, PBNServerBase):
    domain: str
    ssh_private_key: str
    provider_type: ServerProviderType
    public_net_ipv4: str


class ServerRequest(StrToJSONMixin, BaseModel):
    domain_name: str
    ssh_private_key: str
    server_ip: str
    username: str


class PBNServerWPSetup(ServerRequest):
    template_url: str

    @field_validator("template_url", mode="before")
    @classmethod
    def validate_template_url(cls, value: str) -> str:
        return quote(value, safe=":/?=")


class PBNServerDeploy(PBNServerBase):
    url: str
    wp_token: str
    wp_port: str
    host: str

    @property
    def upload_pbn_url(self) -> str:
        return f"http://{self.host}:{self.wp_port}/"


PickledPBNServerStatusCheck = Annotated[bytes, "Pickled[PBNServerStatusCheck"]
PickledPBNServerSetup = Annotated[bytes, "Pickled[PBNServerSetup]"]
PickledPBNServerDeploy = Annotated[bytes, "Pickled[PBNServerDeploy]"]
