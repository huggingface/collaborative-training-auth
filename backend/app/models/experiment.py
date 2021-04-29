from typing import Optional

from app.models.core import CoreModel, DateTimeModelMixin, IDModelMixin


class ExperimentBase(CoreModel):
    """
    All common characteristics of our Experiment resource
    """

    name: Optional[str]
    owner: Optional[str]


class ExperimentCreate(CoreModel):
    name: str


class ExperimentUpdate(ExperimentBase):
    pass


class ExperimentInDB(IDModelMixin, DateTimeModelMixin, ExperimentBase):
    name: str
    owner: str


class ExperimentPublic(IDModelMixin, DateTimeModelMixin, ExperimentBase):
    pass
