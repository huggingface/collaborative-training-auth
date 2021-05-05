from typing import List, Optional

from app.models.collaborator import CollaboratorPublic
from app.models.core import CoreModel, IDModelMixin
from app.models.experiment import (
    ExperimentBase,
    ExperimentCreate,
    ExperimentCreatePublic,
    ExperimentInDB,
    ExperimentPublic,
    ExperimentUpdate,
)
from app.models.user import UserCreate, UserInDB


class ExperimentFullBase(ExperimentBase):
    """
    All common characteristics of our Experiment resource
    """

    pass


class ExperimentFullCreatePublic(ExperimentCreatePublic):
    collaborators: Optional[List[UserCreate]]


class ExperimentFullCreate(ExperimentCreate):
    collaborators: Optional[List[UserCreate]]


class ExperimentFullUpdate(ExperimentUpdate):
    added_collaborators: Optional[List[UserCreate]]
    removed_collaborators: Optional[List[UserCreate]]


class ExperimentFullInDB(ExperimentInDB):
    name: str
    owner: str
    collaborators: Optional[List[UserInDB]]


class ExperimentFullPublic(ExperimentPublic):
    name: Optional[str]
    owner: Optional[str]
    collaborators: Optional[List[CollaboratorPublic]]


class DeletedExperimentFullPublic(IDModelMixin, CoreModel):
    user_ids: Optional[List[int]]
    whitelist_ids: Optional[List[int]]
    collaborators_ids: Optional[List[int]]
