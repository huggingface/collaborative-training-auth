from typing import List

from app.db.repositories.base import BaseRepository
from app.models.collaborator import CollaboratorCreate, CollaboratorInDB


GET_COLLABORATOR_BY_ID_QUERY = """
    SELECT id, user_id, whitelist_item_id, peer_public_key, created_at, updated_at
    FROM collaborators
    WHERE id = :id;
"""
LIST_ALL_COLLABORATOR_BY_WHITELIST_ITEM_ID_QUERY = """
    SELECT id, user_id, whitelist_item_id, peer_public_key, created_at, updated_at
    FROM collaborators
    WHERE whitelist_item_id = :whitelist_item_id;
"""
LIST_ALL_USER_ID_COLLABORATORS_QUERY = """
    SELECT id, user_id, whitelist_item_id, peer_public_key, created_at, updated_at
    FROM collaborators
    WHERE user_id = :user_id;
"""
REGISTER_NEW_COLLABORATOR_QUERY = """
    INSERT INTO collaborators (user_id, whitelist_item_id, peer_public_key)
    VALUES (:user_id, :whitelist_item_id, :peer_public_key)
    RETURNING id, user_id, whitelist_item_id, peer_public_key, created_at, updated_at;
"""
DELETE_COLLABORATOR_BY_ID_QUERY = """
    DELETE FROM collaborators
    WHERE id = :id
    RETURNING id;
"""


class CollaboratorsRepository(BaseRepository):
    async def get_collaborator_by_id(self, *, id: int) -> CollaboratorInDB:
        collaborator = await self.db.fetch_one(query=GET_COLLABORATOR_BY_ID_QUERY, values={"id": id})

        if collaborator:
            user = CollaboratorInDB(**collaborator)
            return user

    async def list_all_collaborator_by_whitelist_item_id(self, *, whitelist_item_id: int) -> List[CollaboratorInDB]:
        collaborators = await self.db.fetch_all(
            query=LIST_ALL_COLLABORATOR_BY_WHITELIST_ITEM_ID_QUERY, values={"whitelist_item_id": whitelist_item_id}
        )

        return [CollaboratorInDB(**collaborator) for collaborator in collaborators]

    async def list_all_user_id_collaborators(self, *, user_id: int) -> List[CollaboratorInDB]:
        collaborators = await self.db.fetch_all(
            query=LIST_ALL_USER_ID_COLLABORATORS_QUERY, values={"user_id": user_id}
        )
        return [CollaboratorInDB(**collaborator) for collaborator in collaborators]

    async def register_new_collaborator(self, *, new_collaborator: CollaboratorCreate) -> CollaboratorInDB:
        created_collaborator = await self.db.fetch_one(
            query=REGISTER_NEW_COLLABORATOR_QUERY, values=new_collaborator.dict()
        )
        return CollaboratorInDB(**created_collaborator)

    async def delete_collaborator_by_id(self, *, id: int) -> int:
        collaborator = await self.get_collaborator_by_id(id=id)
        if not collaborator:
            return None
        deleted_id = await self.db.execute(query=DELETE_COLLABORATOR_BY_ID_QUERY, values={"id": id})
        return deleted_id
