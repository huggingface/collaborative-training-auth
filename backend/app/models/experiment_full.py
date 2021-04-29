from typing import List, Optional

from app.models.core import CoreModel, DateTimeModelMixin, IDModelMixin
from app.models.user import UserCreate, UserInDB


class ExperimentFullBase(CoreModel):
    """
    All common characteristics of our Experiment resource
    """

    pass


class ExperimentFullCreate(ExperimentFullBase):
    name: str
    collaborators: Optional[List[UserCreate]]


class ExperimentFullUpdate(ExperimentFullBase):
    name: Optional[str]
    collaborators: Optional[List[UserCreate]]


class ExperimentFullUpdatePartial(ExperimentFullBase):
    collaborators: Optional[List[UserCreate]]


class ExperimentFullInDB(IDModelMixin, DateTimeModelMixin, ExperimentFullBase):
    name: str
    owner: str
    collaborators: Optional[List[UserInDB]]


class ExperimentFullPublic(IDModelMixin, DateTimeModelMixin, ExperimentFullBase):
    name: Optional[str]
    owner: Optional[str]
    collaborators: Optional[List[UserInDB]]


class DeletedExperimentFullPublic(IDModelMixin, CoreModel):
    collaborators_user_id: Optional[List[int]]
    collaborators_whitelist_id: Optional[List[int]]
