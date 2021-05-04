import datetime
from typing import Optional

from pydantic import IPvAnyAddress, validator

from app.models.core import CoreModel


class ExperimentPassInputBase(CoreModel):
    """
    All common characteristics of our Experiment resource
    """

    peer_public_key: Optional[bytes]  # bytes


class HivemindAccessToken(CoreModel):
    username: str
    peer_public_key: bytes
    expiration_time: datetime.datetime
    signature: bytes


class ExperimentPassBase(CoreModel):
    """
    All common characteristics of our Experiment resource
    """

    coordinator_ip: Optional[IPvAnyAddress]
    coordinator_port: Optional[int]
    hivemind_access_token: HivemindAccessToken
    auth_server_public_key: bytes

    @validator("coordinator_port")
    def validate_port(cls, port):
        if port is None:
            return port

        if int(port) > 2 ** 16:
            raise ValueError("port overflow")
        return port


class ExperimentPassPublic(ExperimentPassBase):
    pass
