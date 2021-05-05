from typing import List

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import APIRouter, Body, Depends, HTTPException, Path
from starlette.status import HTTP_201_CREATED, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND

from app.api.dependencies import crypto
from app.api.dependencies.database import get_repository
from app.db.repositories.collaborators import CollaboratorsRepository
from app.db.repositories.experiments import ExperimentsRepository
from app.db.repositories.users import UsersRepository
from app.db.repositories.whitelist import WhitelistRepository
from app.models.collaborator import CollaboratorCreate, CollaboratorPublic
from app.models.experiment import ExperimentBase, ExperimentCreate, ExperimentUpdate
from app.models.experiment_full import (
    DeletedExperimentFullPublic,
    ExperimentFullCreatePublic,
    ExperimentFullPublic,
    ExperimentFullUpdate,
)
from app.models.experiment_join import ExperimentJoinInput, ExperimentJoinOutput
from app.models.whitelist import WhitelistItemCreate
from app.services.authentication import MoonlandingUser, authenticate


router = APIRouter()


@router.get("/", response_model=List[ExperimentFullPublic], name="experiments:list-all-user-experiments")
async def list_all_user_experiments(
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
    collaborators_repo: CollaboratorsRepository = Depends(get_repository(CollaboratorsRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> List[ExperimentFullPublic]:
    all_user_experiments = await experiments_repo.list_all_user_experiments(requesting_user=user)

    list_exp = []
    for exp in all_user_experiments:
        list_exp.append(
            await retrieve_full_experiment(
                experiment_id=exp.id,
                whitelist_repo=whitelist_repo,
                users_repo=users_repo,
                collaborators_repo=collaborators_repo,
                experiment=exp,
            )
        )

    return list_exp


@router.post(
    "/", response_model=ExperimentFullPublic, name="experiments:create-experiment", status_code=HTTP_201_CREATED
)
async def create_new_experiment(
    new_experiment: ExperimentFullCreatePublic = Body(..., embed=True),
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
    collaborators_repo: CollaboratorsRepository = Depends(get_repository(CollaboratorsRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> ExperimentFullPublic:
    collaborators_list = new_experiment.collaborators

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    new_experiment = new_experiment.dict()

    new_experiment_item = ExperimentCreate(
        **new_experiment,
        auth_server_private_key=crypto.save_private_key(private_key),
        auth_server_public_key=crypto.save_public_key(public_key),
    )
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
        collaborators_repo=collaborators_repo,
        experiment=created_experiment_item,
    )
    return created_experiment_item


@router.get("/{id}/", response_model=ExperimentFullPublic, name="experiments:get-experiment-by-id")
async def get_experiment_by_id(
    id: int,
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
    collaborators_repo: CollaboratorsRepository = Depends(get_repository(CollaboratorsRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> ExperimentFullPublic:

    experiment = await experiments_repo.get_experiment_by_id(id=id)
    if not experiment:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No experiment found with that id.")
    if experiment.owner != user.username:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="You aren't the owner of this experiment")

    experiment_full = await retrieve_full_experiment(
        experiment_id=id,
        whitelist_repo=whitelist_repo,
        users_repo=users_repo,
        collaborators_repo=collaborators_repo,
        experiment=experiment,
    )
    return experiment_full


@router.put("/{id}/", response_model=ExperimentFullPublic, name="experiments:update-experiment-by-id")
async def update_experiment_by_id(
    id: int = Path(..., ge=1, title="The ID of the experiment to update."),
    experiment_full_update: ExperimentFullUpdate = Body(..., embed=True),
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
    collaborators_repo: CollaboratorsRepository = Depends(get_repository(CollaboratorsRepository)),
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

            whitelist_item_already_in_db = await whitelist_repo.get_item_by_ids(experiment_id=id, user_id=new_user.id)
            if whitelist_item_already_in_db is None:
                new_item = WhitelistItemCreate(experiment_id=id, user_id=new_user.id)
                _ = await whitelist_repo.register_new_whitelist_item(new_item=new_item)

    if experiment_full_update.removed_collaborators:
        for collaborator in experiment_full_update.removed_collaborators:
            to_remove_user = await users_repo.get_user_by_username(username=collaborator.username)
            if to_remove_user:
                to_remove_item = await whitelist_repo.get_item_by_ids(experiment_id=id, user_id=to_remove_user.id)

                whitelist_id, user_ids_temp, collaborators_ids_temp = await remove_whitelist_item(
                    whitelist_item_id=to_remove_item.id,
                    whitelist_repo=whitelist_repo,
                    collaborators_repo=collaborators_repo,
                    users_repo=users_repo,
                )

    experiment_update = ExperimentUpdate(**experiment_full_update.dict(exclude_unset=True))
    experiment = await experiments_repo.update_experiment_by_id(id_exp=id, experiment_update=experiment_update)

    updated_experiment = await retrieve_full_experiment(
        experiment_id=id,
        whitelist_repo=whitelist_repo,
        users_repo=users_repo,
        collaborators_repo=collaborators_repo,
        experiment=experiment,
    )
    return updated_experiment


@router.delete("/{id}/", response_model=DeletedExperimentFullPublic, name="experiments:delete-experiment-by-id")
async def delete_experiment_by_id(
    id: int = Path(..., ge=1, title="The ID of the experiment to delete."),
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
    collaborators_repo: CollaboratorsRepository = Depends(get_repository(CollaboratorsRepository)),
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> DeletedExperimentFullPublic:
    experiment = await experiments_repo.get_experiment_by_id(id=id)
    if not experiment:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No experiment found with that id.")
    if experiment.owner != user.username:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="You aren't the owner of this experiment")

    all_experiment_id_items = await whitelist_repo.list_all_experiment_id_items(experiment_id=id)

    whitelist_ids = []
    user_ids = []
    collaborators_ids = []

    for whitelist_item in all_experiment_id_items:
        whitelist_id, user_ids_temp, collaborators_ids_temp = await remove_whitelist_item(
            whitelist_item_id=whitelist_item.id,
            whitelist_repo=whitelist_repo,
            collaborators_repo=collaborators_repo,
            users_repo=users_repo,
        )
        whitelist_ids.append(whitelist_id)
        user_ids.extend(user_ids_temp)
        collaborators_ids.extend(collaborators_ids_temp)

    deleted_id = await experiments_repo.delete_experiment_by_id(id=id)
    if not deleted_id:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No experiment found with that id.")

    deleted_exp = DeletedExperimentFullPublic(
        id=deleted_id,
        user_ids=user_ids,
        whitelist_ids=whitelist_ids,
        collaborators_ids=collaborators_ids,
    )
    return deleted_exp


@router.put("/join/{id}/", response_model=ExperimentJoinOutput, name="experiments:join-experiment-by-id")
async def join_experiment_by_id(
    id: int = Path(..., ge=1, title="The ID of the experiment the user wants to join."),
    experiment_join_input: ExperimentJoinInput = Body(..., embed=True),
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
    collaborators_repo: CollaboratorsRepository = Depends(get_repository(CollaboratorsRepository)),
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> ExperimentJoinOutput:
    experiment = await experiments_repo.get_experiment_by_id(id=id)
    if not experiment:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No experiment found with that id.")

    all_experiment_id_items = await whitelist_repo.list_all_experiment_id_items(experiment_id=id)

    whitelist_item = None
    for whitelist_item_tmp in all_experiment_id_items:
        collaborators_list = await collaborators_repo.list_all_collaborator_by_whitelist_item_id(
            whitelist_item_id=whitelist_item_tmp.id
        )

        # Check if a collaborator in the same experiment hasn't already use the same public key
        for collaborator in collaborators_list:
            if collaborator and collaborator.peer_public_key == experiment_join_input.peer_public_key:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Access to the experiment denied, the public key is already taken.",
                )

        user_db = await users_repo.get_user_by_id(id=whitelist_item_tmp.user_id)

        if user_db.username == user.username:
            whitelist_item = whitelist_item_tmp

    # Check if the username is really whitelisted
    if whitelist_item is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Access to the experiment denied.",
        )

    _ = await collaborators_repo.register_new_collaborator(
        new_collaborator=CollaboratorCreate(
            user_id=whitelist_item.user_id,
            whitelist_item_id=whitelist_item.id,
            peer_public_key=experiment_join_input.peer_public_key,
        ),
    )

    hivemind_access = crypto.create_hivemind_access(
        peer_public_key=experiment_join_input.peer_public_key,
        auth_server_private_key=experiment.auth_server_private_key,
        username=user.username,
    )
    exp_pass = ExperimentJoinOutput(**experiment.dict(), hivemind_access=hivemind_access)
    return exp_pass


async def retrieve_full_experiment(
    experiment_id: int,
    whitelist_repo: WhitelistRepository,
    collaborators_repo: CollaboratorsRepository,
    users_repo: UsersRepository,
    experiment: ExperimentBase,
) -> ExperimentFullPublic:
    all_experiment_id_items = await whitelist_repo.list_all_experiment_id_items(experiment_id=experiment_id)

    collaborators = []
    for whitelist_item in all_experiment_id_items:
        user = await users_repo.get_user_by_id(id=whitelist_item.user_id)
        collaborator_list = await collaborators_repo.list_all_collaborator_by_whitelist_item_id(
            whitelist_item_id=whitelist_item.id
        )
        for collaborator in collaborator_list:
            collaborators.append(
                CollaboratorPublic(
                    username=user.username,
                    peer_public_key=collaborator.peer_public_key,
                    user_created_at=user.created_at,
                    user_updated_at=user.updated_at,
                    public_key_created_at=collaborator.created_at,
                    public_key_updated_at=collaborator.updated_at,
                )
            )
        if collaborator_list == []:
            collaborators.append(
                CollaboratorPublic(
                    username=user.username,
                    user_created_at=user.created_at,
                    user_updated_at=user.updated_at,
                )
            )

    if collaborators != []:
        experiment_full = ExperimentFullPublic(**experiment.dict(), collaborators=collaborators)
    else:
        experiment_full = ExperimentFullPublic(**experiment.dict())
    return experiment_full


async def remove_whitelist_item(
    whitelist_item_id: int,
    whitelist_repo: WhitelistRepository,
    collaborators_repo: CollaboratorsRepository,
    users_repo: UsersRepository,
):
    user_ids = []
    collaborators_ids = []

    to_remove_item = await whitelist_repo.get_item_by_id(id=whitelist_item_id)

    all_user_occurences_in_whitelist = await whitelist_repo.list_all_user_id_items(user_id=to_remove_item.user_id)

    if len(all_user_occurences_in_whitelist) == 1:
        user_ids.append(await users_repo.delete_user_by_id(id=to_remove_item.user_id))

    collaborators_list = await collaborators_repo.list_all_collaborator_by_whitelist_item_id(
        whitelist_item_id=whitelist_item_id
    )
    for collaborator in collaborators_list:
        # raise ValueError(collaborator.id)
        collaborators_ids.append(await collaborators_repo.delete_collaborator_by_id(id=collaborator.id))

    whitelist_id = await whitelist_repo.delete_item_by_id(id=whitelist_item_id)

    return (whitelist_id, user_ids, collaborators_ids)
