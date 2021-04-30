from typing import List, Optional

from app.models.core import CoreModel, DateTimeModelMixin, IDModelMixin
from app.models.experiment import ExperimentBase, ExperimentCreate, ExperimentUpdate
from app.models.user import UserCreate, UserInDB


class ExperimentFullBase(ExperimentBase):
    """
    All common characteristics of our Experiment resource
    """

    pass


class ExperimentFullCreate(ExperimentCreate):
    collaborators: Optional[List[UserCreate]]


class ExperimentFullUpdate(ExperimentUpdate):
    added_collaborators: Optional[List[UserCreate]]
    removed_collaborators: Optional[List[UserCreate]]


class ExperimentFullInDB(IDModelMixin, DateTimeModelMixin, ExperimentBase):
    name: str
    owner: str
    collaborators: Optional[List[UserInDB]]


class ExperimentFullPublic(IDModelMixin, DateTimeModelMixin, ExperimentBase):
    name: Optional[str]
    owner: Optional[str]
    collaborators: Optional[List[UserInDB]]


class DeletedExperimentFullPublic(IDModelMixin, CoreModel):
    collaborators_user_id: Optional[List[int]]
    collaborators_whitelist_id: Optional[List[int]]
