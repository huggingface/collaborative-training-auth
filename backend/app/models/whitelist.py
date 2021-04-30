from app.models.core import CoreModel, DateTimeModelMixin, IDModelMixin


class WhitelistItemBase(CoreModel):
    """
    All common characteristics of our Whitelist resource
    """

    experiment_id: int
    user_id: int


class WhitelistItemCreate(WhitelistItemBase):
    pass


class WhitelistItemUpdate(WhitelistItemBase):
    pass


class WhitelistItemInDB(IDModelMixin, DateTimeModelMixin, WhitelistItemBase):
    """
    Add in id, created_at, updated_at
    """

    pass


class WhitelistItemPublic(IDModelMixin, DateTimeModelMixin, WhitelistItemBase):
    pass
