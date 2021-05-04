import base64
import datetime
from typing import List

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import APIRouter, Body, Depends, HTTPException, Path
from starlette.status import HTTP_201_CREATED, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND

from app.api.dependencies.database import get_repository
from app.core.config import EXPIRATION_MINUTES
from app.db.repositories import crypto
from app.db.repositories.experiments import ExperimentsRepository
from app.db.repositories.users import UsersRepository
from app.db.repositories.whitelist import WhitelistRepository
from app.models.experiment import ExperimentBase, ExperimentCreate, ExperimentUpdate
from app.models.experiment_full import (
    DeletedExperimentFullPublic,
    ExperimentFullCreate,
    ExperimentFullInDB,
    ExperimentFullPublic,
    ExperimentFullUpdate,
)
from app.models.experiment_pass import ExperimentPassInputBase, ExperimentPassPublic, HivemindAccessToken
from app.models.whitelist import WhitelistItemCreate, WhitelistItemUpdate
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

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    new_experiment.auth_server_private_key = crypto.save_private_key(private_key)
    new_experiment.auth_server_public_key = crypto.save_public_key(public_key)

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
    if collaborators != []:
        experiment_full = ExperimentFullPublic(**experiment.dict(), collaborators=collaborators)
    else:
        experiment_full = ExperimentFullPublic(**experiment.dict())
    return experiment_full


@router.put("/{id}/", response_model=ExperimentFullPublic, name="experiments:update-experiment-by-id")
async def update_experiment_by_id(
    id: int = Path(..., ge=1, title="The ID of the experiment to update."),
    experiment_full_update: ExperimentFullUpdate = Body(..., embed=True),
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

    if experiment_full_update.added_collaborators:
        for collaborator in experiment_full_update.added_collaborators:
            new_user = await users_repo.get_user_by_username(username=collaborator.username)
            if new_user is None:
                new_user = await users_repo.register_new_user(new_user=collaborator)

            new_item = WhitelistItemCreate(experiment_id=id, user_id=new_user.id)
            _ = await whitelist_repo.register_new_whitelist_item(new_item=new_item)

    if experiment_full_update.removed_collaborators:
        for collaborator in experiment_full_update.removed_collaborators:
            to_remove_user = await users_repo.get_user_by_username(username=collaborator.username)
            if to_remove_user:
                to_remove_item = await whitelist_repo.get_item_by_ids(experiment_id=id, user_id=to_remove_user.id)
                all_user_occurences_in_whitelist = await whitelist_repo.list_all_user_id_items(
                    user_id=to_remove_user.id
                )

                if to_remove_item:
                    _ = await whitelist_repo.delete_item_by_id(id=to_remove_item.id)
                if to_remove_item is not None and to_remove_item.id in [
                    item.id for item in all_user_occurences_in_whitelist
                ]:
                    _ = await users_repo.delete_user_by_id(id=to_remove_user.id)

    experiment_update = ExperimentUpdate(**experiment_full_update.dict(exclude_unset=True))
    experiment = await experiments_repo.update_experiment_by_id(id_exp=id, experiment_update=experiment_update)

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


@router.put("/join/{id}/", response_model=ExperimentPassPublic, name="experiments:join-experiment-by-id")
async def join_experiment_by_id(
    id: int = Path(..., ge=1, title="The ID of the experiment the user wants to join."),
    experiment_pass_input: ExperimentPassInputBase = Body(..., embed=True),
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> ExperimentPassPublic:
    experiment = await experiments_repo.get_experiment_by_id(id=id)
    if not experiment:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No experiment found with that id.")

    all_experiment_id_items = await whitelist_repo.list_all_experiment_id_items(experiment_id=id)

    collaborators = []
    for whitelist_item in all_experiment_id_items:
        collaborators.append(await users_repo.get_user_by_id(id=whitelist_item.user_id))
        if whitelist_item.peer_public_key == experiment_pass_input.peer_public_key:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Access to the experiment denied, the public key is already taken.",
            )

    if collaborators != []:
        experiment_full = ExperimentFullInDB(**experiment.dict(), collaborators=collaborators)
    else:
        experiment_full = ExperimentFullInDB(**experiment.dict())

    if experiment_full.collaborators is None:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Access to the experiment denied.")

    user_id = [
        collaborator.id
        for collaborator in experiment_full.collaborators
        if collaborator.username.lower() == user.username.lower()
    ]

    if len(user_id) != 1:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Access to the experiment denied.",
        )

    _ = await whitelist_repo.update_item_by_ids(
        experiment_id=id,
        user_id=user_id[0],
        item_update=WhitelistItemUpdate(peer_public_key=experiment_pass_input.peer_public_key),
    )

    hivemind_access_token = create_hivemind_access_token(
        experiment_pass_input=experiment_pass_input,
        auth_server_private_key=experiment_full.auth_server_private_key,
        username=user.username.lower(),
    )
    exp_pass = ExperimentPassPublic(**experiment_full.dict(), hivemind_access_token=hivemind_access_token)
    return exp_pass


def create_hivemind_access_token(
    experiment_pass_input: ExperimentPassInputBase, auth_server_private_key: bytes, username: str
):
    current_time = datetime.datetime.utcnow()
    expiration_time = current_time + datetime.timedelta(minutes=EXPIRATION_MINUTES)

    private_key = crypto.load_private_key(auth_server_private_key)
    signature = private_key.sign(
        f"{username} {experiment_pass_input.peer_public_key} {expiration_time}".encode(),
        crypto.PADDING,
        crypto.HASH_ALGORITHM,
    )
    signature = base64.b64encode(signature)

    hivemind_access_token = HivemindAccessToken(
        username=username,
        peer_public_key=experiment_pass_input.peer_public_key,
        expiration_time=expiration_time,
        signature=signature,
    )
    return hivemind_access_token


async def retrieve_full_experiment(
    experiment_id: int,
    whitelist_repo: WhitelistRepository,
    users_repo: UsersRepository,
    experiment: ExperimentBase,
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
