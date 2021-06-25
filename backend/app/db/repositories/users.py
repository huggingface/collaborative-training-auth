#
# Copyright (c) 2021 the Hugging Face team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.#
from fastapi import HTTPException, status

from app.db.repositories.base import BaseRepository
from app.models.user import UserCreate, UserInDB


GET_USER_BY_ID_QUERY = """
    SELECT id, username, created_at, updated_at
    FROM users
    WHERE id = :id;
"""

GET_USER_BY_USERNAME_QUERY = """
    SELECT id, username, created_at, updated_at
    FROM users
    WHERE username = :username;
"""

REGISTER_NEW_USER_QUERY = """
    INSERT INTO users (username)
    VALUES (:username)
    RETURNING id, username, created_at, updated_at;
"""
DELETE_USER_BY_ID_QUERY = """
    DELETE FROM users
    WHERE id = :id
    RETURNING id;
"""


class UsersRepository(BaseRepository):
    async def get_user_by_username(self, *, username: str) -> UserInDB:
        user_record = await self.db.fetch_one(query=GET_USER_BY_USERNAME_QUERY, values={"username": username})

        if user_record:
            user = UserInDB(**user_record)

            return user

    async def get_user_by_id(self, *, id: int) -> UserInDB:
        user_record = await self.db.fetch_one(query=GET_USER_BY_ID_QUERY, values={"id": id})

        if user_record:
            user = UserInDB(**user_record)

            return user

    async def register_new_user(self, *, new_user: UserCreate) -> UserInDB:
        if await self.get_user_by_username(username=new_user.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="That username is already taken. Please try another one.",
            )

        created_user = await self.db.fetch_one(query=REGISTER_NEW_USER_QUERY, values=new_user.dict())

        return UserInDB(**created_user)

    async def delete_user_by_id(self, *, id: int) -> int:
        experiment = await self.get_user_by_id(id=id)
        if not experiment:
            return None
        deleted_id = await self.db.execute(query=DELETE_USER_BY_ID_QUERY, values={"id": id})
        return deleted_id
