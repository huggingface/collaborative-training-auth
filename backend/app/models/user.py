from app.models.core import CoreModel, DateTimeModelMixin, IDModelMixin


class UserBase(CoreModel):
    """
    All common characteristics of our User resource
    """

    pass


class UserCreate(CoreModel):
    """
    username are required for registering a new user
    """

    username: str


class UserUpdate(CoreModel):
    pass


class UserInDB(IDModelMixin, DateTimeModelMixin, UserBase):
    """
    Add in id, created_at, updated_at
    """

    username: str


class UserPublic(IDModelMixin, DateTimeModelMixin, UserBase):
    username: str
