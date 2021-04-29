from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException, Path
from starlette.status import HTTP_201_CREATED, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND

from app.api.dependencies.database import get_repository
from app.db.repositories.experiments import ExperimentsRepository
from app.db.repositories.users import UsersRepository
from app.db.repositories.whitelist import WhitelistRepository
from app.models.experiment import ExperimentBase, ExperimentCreate
from app.models.experiment_full import (
    DeletedExperimentFullPublic,
    ExperimentFullCreate,
    ExperimentFullPublic,
    ExperimentFullUpdatePartial,
)
from app.models.whitelist import WhitelistItemCreate
from app.services.authentication import MoonlandingUser, authenticate


router = APIRouter()


@router.get("/", response_model=List[ExperimentFullPublic], name="experiments:list-all-user-experiments")
async def list_all_user_experiments(
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> List[ExperimentFullPublic]:
    all_user_experiments = await experiments_repo.list_all_user_experiments(requesting_user=user)

    list_exp = []
    for exp in all_user_experiments:
        list_exp.append(
            await retrieve_full_experiment(
                experiment_id=exp.id, whitelist_repo=whitelist_repo, users_repo=users_repo, experiment=exp
            )
        )

    return list_exp


@router.post(
    "/", response_model=ExperimentFullPublic, name="experiments:create-experiment", status_code=HTTP_201_CREATED
)
async def create_new_experiment(
    new_experiment: ExperimentFullCreate = Body(..., embed=True),
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> ExperimentFullPublic:
    collaborators_list = new_experiment.collaborators

    new_experiment = new_experiment.dict()

    new_experiment_item = ExperimentCreate(**new_experiment)
    created_experiment_item = await experiments_repo.create_experiment(
        new_experiment=new_experiment_item, requesting_user=user
    )

    if collaborators_list:
        for collaborator in collaborators_list:
            new_user = await users_repo.get_user_by_username(username=collaborator.username)
            if new_user is None:
                new_user = await users_repo.register_new_user(new_user=collaborator)

            new_item = WhitelistItemCreate(experiment_id=created_experiment_item.id, user_id=new_user.id)
            _ = await whitelist_repo.register_new_whitelist_item(new_item=new_item)

    created_experiment_item = await retrieve_full_experiment(
        experiment_id=created_experiment_item.id,
        whitelist_repo=whitelist_repo,
        users_repo=users_repo,
        experiment=created_experiment_item,
    )
    return created_experiment_item


@router.get("/{id}/", response_model=ExperimentFullPublic, name="experiments:get-experiment-by-id")
async def get_experiment_by_id(
    id: int,
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> ExperimentFullPublic:

    experiment = await experiments_repo.get_experiment_by_id(id=id)
    if not experiment:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No experiment found with that id.")
    if experiment.owner != user.username:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="You aren't the owner of this experiment")

    all_experiment_id_items = await whitelist_repo.list_all_experiment_id_items(experiment_id=experiment.id)

    collaborators = []
    for whitelist_item in all_experiment_id_items:
        collaborators.append(await users_repo.get_user_by_id(id=whitelist_item.user_id))
    # raise ValueError(collaborators)
    if collaborators != []:
        experiment_full = ExperimentFullPublic(**experiment.dict(), collaborators=collaborators)
    else:
        experiment_full = ExperimentFullPublic(**experiment.dict())
    # raise ValueError(experiment_full)
    return experiment_full


@router.put("/{id}/", response_model=ExperimentFullPublic, name="experiments:add-new-collaborators-to-experiment")
async def update_experiment_by_id(
    id: int = Path(..., ge=1, title="The ID of the experiment to update."),
    experiment_update: ExperimentFullUpdatePartial = Body(..., embed=True),
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> ExperimentFullPublic:
    experiment = await experiments_repo.get_experiment_by_id(id=id)
    if not experiment:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No experiment found with that id.")
    if experiment.owner != user.username:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="You aren't the owner of this experiment")

    if experiment_update.collaborators:
        for collaborator in experiment_update.collaborators:
            new_user = await users_repo.get_user_by_username(username=collaborator.username)
            if new_user is None:
                new_user = await users_repo.register_new_user(new_user=collaborator)

            new_item = WhitelistItemCreate(experiment_id=id, user_id=new_user.id)
            _ = await whitelist_repo.register_new_whitelist_item(new_item=new_item)

    updated_experiment = await retrieve_full_experiment(
        experiment_id=id, whitelist_repo=whitelist_repo, users_repo=users_repo, experiment=experiment
    )
    return updated_experiment


@router.delete("/{id}/", response_model=DeletedExperimentFullPublic, name="experiments:delete-experiment-by-id")
async def delete_experiment_by_id(
    id: int = Path(..., ge=1, title="The ID of the experiment to delete."),
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> DeletedExperimentFullPublic:
    experiment = await experiments_repo.get_experiment_by_id(id=id)
    if not experiment:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No experiment found with that id.")
    if experiment.owner != user.username:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="You aren't the owner of this experiment")

    all_experiment_id_items = await whitelist_repo.list_all_experiment_id_items(experiment_id=id)

    collaborators_whitelist_id = []
    collaborators_user_id = []

    for whitelist_item in all_experiment_id_items:
        all_user_occurences_in_whitelist = await whitelist_repo.list_all_user_id_items(user_id=whitelist_item.user_id)
        collaborators_whitelist_id.append(await whitelist_repo.delete_item_by_id(id=whitelist_item.id))
        if len(all_user_occurences_in_whitelist) == 1:
            collaborators_user_id.append(await users_repo.delete_user_by_id(id=whitelist_item.user_id))

    deleted_id = await experiments_repo.delete_experiment_by_id(id=id)
    if not deleted_id:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No experiment found with that id.")

    deleted_exp = DeletedExperimentFullPublic(
        id=deleted_id,
        collaborators_user_id=collaborators_user_id,
        collaborators_whitelist_id=collaborators_whitelist_id,
    )
    return deleted_exp


async def retrieve_full_experiment(
    experiment_id: int, whitelist_repo: WhitelistRepository, users_repo: UsersRepository, experiment: ExperimentBase
) -> ExperimentFullPublic:
    all_experiment_id_items = await whitelist_repo.list_all_experiment_id_items(experiment_id=experiment_id)

    collaborators = []
    for whitelist_item in all_experiment_id_items:
        collaborators.append(await users_repo.get_user_by_id(id=whitelist_item.user_id))
    if collaborators != []:
        experiment_full = ExperimentFullPublic(**experiment.dict(), collaborators=collaborators)
    else:
        experiment_full = ExperimentFullPublic(**experiment.dict())
    return experiment_full
