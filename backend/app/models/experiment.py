from typing import Optional

from pydantic import IPvAnyAddress, validator

from app.models.core import CoreModel, DateTimeModelMixin, IDModelMixin


class ExperimentBase(CoreModel):
    """
    All common characteristics of our Experiment resource
    """

    name: Optional[str]
    coordinator_ip: Optional[IPvAnyAddress]
    coordinator_port: Optional[int]

    @validator("coordinator_port")
    def validate_port(cls, port):
        if port is None:
            return port

        if int(port) > 2 ** 16:
            raise ValueError("port overflow")
        return port


class ExperimentCreate(CoreModel):
    name: str


class ExperimentUpdate(ExperimentBase):
    pass


class ExperimentInDB(IDModelMixin, DateTimeModelMixin, ExperimentBase):
    name: str
    owner: str


class ExperimentPublic(IDModelMixin, DateTimeModelMixin, ExperimentBase):
    owner: str
