from datetime import datetime
from typing import Optional

from app.models.core import CoreModel, DateTimeModelMixin, IDModelMixin


class CollaboratorBase(CoreModel):
    """
    All common characteristics of our Collaborator resource
    """

    user_id: int
    whitelist_item_id: int
    peer_public_key: bytes


class CollaboratorCreate(CollaboratorBase):
    """
    username are required for registering a new user
    """

    pass


class CollaboratorUpdate(CollaboratorBase):
    pass


class CollaboratorInDB(IDModelMixin, DateTimeModelMixin, CollaboratorBase):
    """
    Add in id, created_at, updated_at
    """

    pass


class CollaboratorPublic(CoreModel):
    username: str
    peer_public_key: Optional[bytes]
    user_created_at: Optional[datetime]
    user_updated_at: Optional[datetime]
    public_key_created_at: Optional[datetime]
    public_key_updated_at: Optional[datetime]
