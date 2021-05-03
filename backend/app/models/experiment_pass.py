from typing import Optional

from pydantic import IPvAnyAddress, validator

from app.models.core import CoreModel


class ExperimentPassBase(CoreModel):
    """
    All common characteristics of our Experiment resource
    """

    coordinator_ip: Optional[IPvAnyAddress]
    coordinator_port: Optional[int]

    @validator("coordinator_port")
    def validate_port(cls, port):
        if port is None:
            return port

        if int(port) > 2 ** 16:
            raise ValueError("port overflow")
        return port


class ExperimentPassPublic(ExperimentPassBase):
    pass
