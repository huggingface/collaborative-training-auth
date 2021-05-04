from typing import List

from fastapi import HTTPException, status

from app.db.repositories.base import BaseRepository
from app.models.whitelist import WhitelistItemCreate, WhitelistItemInDB, WhitelistItemUpdate


GET_ITEM_BY_ID_QUERY = """
    SELECT id, experiment_id, user_id, peer_public_key, created_at, updated_at
    FROM whitelist
    WHERE id = :id;
"""
GET_ITEM_BY_IDS_QUERY = """
    SELECT id, experiment_id, user_id, peer_public_key, created_at, updated_at
    FROM whitelist
    WHERE experiment_id = :experiment_id AND user_id = :user_id;
"""
UPDATE_ITEM_BY_ID_QUERY = """
    UPDATE whitelist
    SET peer_public_key = :peer_public_key
    WHERE experiment_id = :experiment_id AND user_id = :user_id
    RETURNING id, experiment_id, user_id, peer_public_key, created_at, updated_at;
"""
LIST_ALL_EXPERIMENT_ID_ITEMS_QUERY = """
    SELECT id, experiment_id, user_id, peer_public_key, created_at, updated_at
    FROM whitelist
    WHERE experiment_id = :experiment_id;
"""
LIST_ALL_USER_ID_ITEMS_QUERY = """
    SELECT id, experiment_id, user_id, peer_public_key, created_at, updated_at
    FROM whitelist
    WHERE user_id = :user_id;
"""
REGISTER_NEW_WHITELIST_ITEM_QUERY = """
    INSERT INTO whitelist (experiment_id, user_id)
    VALUES (:experiment_id, :user_id)
    RETURNING id, experiment_id, user_id, peer_public_key, created_at, updated_at;
"""
DELETE_EXPERIMENT_BY_ID_QUERY = """
    DELETE FROM whitelist
    WHERE id = :id
    RETURNING id;
"""


class WhitelistRepository(BaseRepository):
    async def get_item_by_id(self, *, id: int) -> WhitelistItemInDB:
        item_record = await self.db.fetch_one(query=GET_ITEM_BY_ID_QUERY, values={"id": id})

        if item_record:
            user = WhitelistItemInDB(**item_record)
            return user

    async def get_item_by_ids(self, *, experiment_id: int, user_id: int) -> WhitelistItemInDB:
        item_record = await self.db.fetch_one(
            query=GET_ITEM_BY_IDS_QUERY, values={"experiment_id": experiment_id, "user_id": user_id}
        )

        if item_record:
            user = WhitelistItemInDB(**item_record)

            return user

    async def update_item_by_ids(
        self, *, experiment_id: int, user_id: int, item_update: WhitelistItemUpdate
    ) -> WhitelistItemInDB:
        item = await self.get_item_by_ids(experiment_id=experiment_id, user_id=user_id)
        if not item:
            return None
        item_update_params = item.copy(update=item_update.dict(exclude_unset=True))
        values = {
            **item_update_params.dict(
                exclude={
                    "id",
                    "created_at",
                    "updated_at",
                }
            )
        }
        try:
            updated_experiment = await self.db.fetch_one(query=UPDATE_ITEM_BY_ID_QUERY, values=values)
        except Exception as e:
            print(e)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid update params.")
        return WhitelistItemInDB(**updated_experiment)

    async def list_all_experiment_id_items(self, *, experiment_id: int) -> List[WhitelistItemInDB]:
        experiment_records = await self.db.fetch_all(
            query=LIST_ALL_EXPERIMENT_ID_ITEMS_QUERY, values={"experiment_id": experiment_id}
        )
        return [WhitelistItemInDB(**exp) for exp in experiment_records]

    async def list_all_user_id_items(self, *, user_id: int) -> List[WhitelistItemInDB]:
        experiment_records = await self.db.fetch_all(query=LIST_ALL_USER_ID_ITEMS_QUERY, values={"user_id": user_id})
        return [WhitelistItemInDB(**exp) for exp in experiment_records]

    async def register_new_whitelist_item(self, *, new_item: WhitelistItemCreate) -> WhitelistItemInDB:
        if await self.get_item_by_ids(experiment_id=new_item.experiment_id, user_id=new_item.user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="That couple of (experiment_id, user_id) is already registered",
            )
        created_item = await self.db.fetch_one(query=REGISTER_NEW_WHITELIST_ITEM_QUERY, values=new_item.dict())
        return WhitelistItemInDB(**created_item)

    async def delete_item_by_id(self, *, id: int) -> int:
        item = await self.get_item_by_id(id=id)
        if not item:
            return None
        deleted_id = await self.db.execute(query=DELETE_EXPERIMENT_BY_ID_QUERY, values={"id": id})
        return deleted_id
