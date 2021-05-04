from typing import Optional

from app.models.core import CoreModel, DateTimeModelMixin, IDModelMixin


class WhitelistItemBase(CoreModel):
    """
    All common characteristics of our Whitelist resource
    """

    pass


class WhitelistItemCreate(WhitelistItemBase):
    experiment_id: int
    user_id: int


class WhitelistItemUpdate(WhitelistItemBase):
    peer_public_key: Optional[str]


class WhitelistItemInDB(IDModelMixin, DateTimeModelMixin, WhitelistItemBase):
    """
    Add in id, created_at, updated_at
    """

    experiment_id: int
    user_id: int
    peer_public_key: Optional[str]


class WhitelistItemPublic(IDModelMixin, DateTimeModelMixin, WhitelistItemBase):
    pass
