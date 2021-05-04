import datetime
from typing import Optional

from pydantic import IPvAnyAddress, validator

from app.models.core import CoreModel


class HivemindAccess(CoreModel):
    username: str
    peer_public_key: bytes
    expiration_time: datetime.datetime
    signature: bytes


class ExperimentJoinInput(CoreModel):
    """
    All common characteristics of our Experiment resource
    """

    peer_public_key: Optional[bytes]  # bytes


class ExperimentJoinOutput(CoreModel):
    """
    All common characteristics of our Experiment resource
    """

    coordinator_ip: Optional[IPvAnyAddress]
    coordinator_port: Optional[int]
    hivemind_access: HivemindAccess
    auth_server_public_key: bytes

    @validator("coordinator_port")
    def validate_port(cls, port):
        if port is None:
            return port

        if int(port) > 2 ** 16:
            raise ValueError("port overflow")
        return port
