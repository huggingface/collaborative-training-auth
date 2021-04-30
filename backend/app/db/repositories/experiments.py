from ipaddress import IPv4Address, IPv6Address
from typing import List

from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST

from app.db.repositories.base import BaseRepository
from app.models.experiment import ExperimentCreate, ExperimentInDB, ExperimentUpdate
from app.services.authentication import MoonlandingUser


CREATE_EXPERIMENT_QUERY = """
    INSERT INTO experiments (name, owner)
    VALUES (:name, :owner)
    RETURNING id, name, owner, coordinator_ip, coordinator_port, created_at, updated_at;
"""
GET_EXPERIMENT_BY_ID_QUERY = """
    SELECT id, name, owner, coordinator_ip, coordinator_port, created_at, updated_at
    FROM experiments
    WHERE id = :id;
"""
LIST_ALL_USER_EXPERIMENTS_QUERY = """
    SELECT id, name, owner, coordinator_ip, coordinator_port, created_at, updated_at
    FROM experiments
    WHERE owner = :owner;
"""
UPDATE_EXPERIMENT_BY_ID_QUERY = """
    UPDATE experiments
    SET name             = :name,
        coordinator_ip   = :coordinator_ip,
        coordinator_port = :coordinator_port,
        owner            = :owner
    WHERE id = :id
    RETURNING id, name, owner, coordinator_ip, coordinator_port, created_at, updated_at;
"""
DELETE_EXPERIMENT_BY_ID_QUERY = """
    DELETE FROM experiments
    WHERE id = :id
    RETURNING id;
"""


class ExperimentsRepository(BaseRepository):
    """ "
    All database actions associated with the Experiment resource
    """

    async def create_experiment(
        self, *, new_experiment: ExperimentCreate, requesting_user: MoonlandingUser
    ) -> ExperimentInDB:
        new_experiment_table = {**new_experiment.dict(), "owner": requesting_user.username}
        experiment = await self.db.fetch_one(query=CREATE_EXPERIMENT_QUERY, values=new_experiment_table)
        return ExperimentInDB(**experiment)

    async def get_experiment_by_id(self, *, id: int) -> ExperimentInDB:
        experiment = await self.db.fetch_one(query=GET_EXPERIMENT_BY_ID_QUERY, values={"id": id})
        if not experiment:
            return None

        return ExperimentInDB(**experiment)

    async def list_all_user_experiments(self, requesting_user: MoonlandingUser) -> List[ExperimentInDB]:
        experiment_records = await self.db.fetch_all(
            query=LIST_ALL_USER_EXPERIMENTS_QUERY, values={"owner": requesting_user.username}
        )
        return [ExperimentInDB(**exp) for exp in experiment_records]

    async def update_experiment_by_id(self, *, id_exp: int, experiment_update: ExperimentUpdate) -> ExperimentInDB:

        experiment = await self.get_experiment_by_id(id=id_exp)
        if not experiment:
            return None
        experiment_update_params = experiment.copy(update=experiment_update.dict(exclude_unset=True))
        values = {**experiment_update_params.dict(exclude={"collaborators", "created_at", "updated_at"})}
        # raise ValueError(
        #     f"experiment: {experiment}\nexperiment_update.dict(exclude_unset=True): {experiment_update.dict(exclude_unset=True)}\nexperiment_update_params: {experiment_update_params}\nvalues: {values}"
        # )
        if "coordinator_ip" in values.keys() and (
            isinstance(values["coordinator_ip"], IPv4Address) or isinstance(values["coordinator_ip"], IPv6Address)
        ):
            values["coordinator_ip"] = str(values["coordinator_ip"])
        try:
            updated_experiment = await self.db.fetch_one(query=UPDATE_EXPERIMENT_BY_ID_QUERY, values=values)
        except Exception as e:
            print(e)
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid update params.")
        return ExperimentInDB(**updated_experiment)

    async def delete_experiment_by_id(self, *, id: int) -> int:
        experiment = await self.get_experiment_by_id(id=id)
        if not experiment:
            return None
        deleted_id = await self.db.execute(query=DELETE_EXPERIMENT_BY_ID_QUERY, values={"id": id})
        return deleted_id
