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
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import APIRouter, Body, Depends, HTTPException, Path
from starlette.status import HTTP_201_CREATED, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND

from app.api.dependencies import crypto
from app.api.dependencies.database import get_repository
from app.db.repositories.collaborators import CollaboratorsRepository
from app.db.repositories.experiments import ExperimentsRepository
from app.db.repositories.users import UsersRepository
from app.db.repositories.whitelist import WhitelistRepository
from app.models.experiment import (
    ExperimentCreate,
    ExperimentCreatePublic,
    ExperimentInDB,
    ExperimentPublic,
    ExperimentUpdate,
)
from app.models.experiment_join import ExperimentJoinInput, ExperimentJoinOutput
from app.services.authentication import MoonlandingUser, RepoRole, authenticate


router = APIRouter()

# Todo Delete
# @router.get("/", response_model=List[ExperimentFullPublic], name="experiments:list-all-user-experiments")
# async def list_all_user_experiments(
#     experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
#     users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
#     whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
#     collaborators_repo: CollaboratorsRepository = Depends(get_repository(CollaboratorsRepository)),
#     user: MoonlandingUser = Depends(authenticate),
# ) -> List[ExperimentFullPublic]:
#     all_user_experiments = await experiments_repo.list_all_user_experiments(requesting_user=user)

#     list_exp = []
#     for exp in all_user_experiments:
#         list_exp.append(
#             await retrieve_full_experiment(
#                 experiment_id=exp.id,
#                 whitelist_repo=whitelist_repo,
#                 users_repo=users_repo,
#                 collaborators_repo=collaborators_repo,
#                 experiment=exp,
#             )
#         )

#     return list_exp


@router.post("/", response_model=ExperimentPublic, name="experiments:create-experiment", status_code=HTTP_201_CREATED)
async def create_new_experiment(
    new_experiment: ExperimentCreatePublic = Body(..., embed=True),
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> ExperimentPublic:
    # collaborators_list = new_experiment.collaborators

    if new_experiment.organization_name not in [org.name for org in user.orgs if org.role_in_org == RepoRole.admin]:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"You need to be an admin of the organization {new_experiment.organization_name} to create a collaborative experiment for the model {new_experiment.model_name}",
        )

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

    # TODO Delete
    # if collaborators_list:
    #     for collaborator in collaborators_list:
    #         new_user = await users_repo.get_user_by_username(username=collaborator.username)
    #         if new_user is None:
    #             new_user = await users_repo.register_new_user(new_user=collaborator)

    #         new_item = WhitelistItemCreate(experiment_id=created_experiment_item.id, user_id=new_user.id)
    #         _ = await whitelist_repo.register_new_whitelist_item(new_item=new_item)

    # TODO
    created_experiment_item = await get_experiment_by_id(
        id=created_experiment_item.id,
        experiments_repo=experiments_repo,
        user=user,
    )
    return created_experiment_item


@router.get("/{id}/", response_model=ExperimentPublic, name="experiments:get-experiment-by-id")
async def get_experiment_by_id(
    id: int,
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    # users_repo: UsersRepository = Depends(get_repository(UsersRepository)), TODO delete
    # whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
    # collaborators_repo: CollaboratorsRepository = Depends(get_repository(CollaboratorsRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> ExperimentPublic:

    experiment = await experiments_repo.get_experiment_by_id(id=id)

    if not experiment:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="You need to be an admin of the organization to get the collaborative experiment for the model",
        )

    if experiment.organization_name not in [org.name for org in user.orgs if org.role_in_org == RepoRole.admin]:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"You need to be an admin of the organization {experiment.organization_name} to get the collaborative experiment for the model {experiment.model_name}",
        )

    # TODO Delete
    # if experiment.owner != user.username:
    #     raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="You aren't the owner of this experiment")

    experiment_public = ExperimentPublic(**experiment.dict())
    return experiment_public


@router.get(
    "/{id}/", response_model=ExperimentPublic, name="experiments:get-experiment-by-organization-and-model-name"
)
async def get_experiment_by_organization_and_model_name(
    organization_name: str,
    model_name: str,
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    # users_repo: UsersRepository = Depends(get_repository(UsersRepository)), TODO delete
    # whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
    # collaborators_repo: CollaboratorsRepository = Depends(get_repository(CollaboratorsRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> ExperimentPublic:
    # TODO
    pass


@router.put("/{id}/", response_model=ExperimentPublic, name="experiments:update-experiment-by-id")
async def update_experiment_by_id(
    id: int = Path(..., ge=1, title="The ID of the experiment to update."),
    experiment_update: ExperimentUpdate = Body(..., embed=True),
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> ExperimentPublic:
    experiment = await experiments_repo.get_experiment_by_id(id=id)

    if not experiment:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="You need to be an admin of the organization to update the collaborative experiment for the model",
        )

    if experiment.organization_name not in [org.name for org in user.orgs if org.role_in_org == RepoRole.admin]:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"You need to be an admin of the organization {experiment.organization_name} to update the collaborative experiment for the model {experiment.model_name}",
        )

    if not experiment:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No experiment found with that id.")

    updated_public_experiment = await update_experiment(experiment, experiment_update, user, experiments_repo)
    return updated_public_experiment


@router.put(
    "/{id}/", response_model=ExperimentPublic, name="experiments:update-experiment-by-organization-and-model-name"
)
async def update_experiment_by_organization_and_model_name(
    id: int = Path(..., ge=1, title="The ID of the experiment to update."),
    experiment_update: ExperimentUpdate = Body(..., embed=True),
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
    collaborators_repo: CollaboratorsRepository = Depends(get_repository(CollaboratorsRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> ExperimentPublic:
    # TODO
    pass


async def update_experiment(
    experiment: ExperimentInDB,
    experiment_update: ExperimentUpdate,
    user: MoonlandingUser,
    experiments_repo: ExperimentsRepository,
):
    experiment_update = ExperimentUpdate(**experiment_update.dict(exclude_unset=True))
    experiment = await experiments_repo.update_experiment_by_id(
        id_exp=experiment.id, experiment_update=experiment_update
    )

    updated_public_experiment = await get_experiment_by_id(
        id=experiment.id,
        experiments_repo=experiments_repo,
        user=user,
    )
    return updated_public_experiment


@router.delete("/{id}/", response_model=ExperimentPublic, name="experiments:delete-experiment-by-id")
async def delete_experiment_by_id(
    id: int = Path(..., ge=1, title="The ID of the experiment to delete."),
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> ExperimentPublic:
    experiment = await experiments_repo.get_experiment_by_id(id=id)

    if not experiment:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="You need to be an admin of the organization to update the collaborative experiment for the model",
        )

    if experiment.organization_name not in [org.name for org in user.orgs if org.role_in_org == RepoRole.admin]:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"You need to be an admin of the organization {experiment.organization_name} to delete the collaborative experiment for the model {experiment.model_name}",
        )
    if not experiment:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No experiment found with that id.")

    deleted_public_experiment = await delete_experiment(experiment, user, experiments_repo)
    return deleted_public_experiment


@router.delete(
    "/{id}/", response_model=ExperimentPublic, name="experiments:delete-experiment-by-organization-and-model-name"
)
async def delete_experiment_by_organization_and_model_name(
    id: int = Path(..., ge=1, title="The ID of the experiment to delete."),
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> ExperimentPublic:
    # TODO
    pass


async def delete_experiment(
    experiment: ExperimentInDB, user: MoonlandingUser, experiments_repo: ExperimentsRepository
):
    deleted_id = await experiments_repo.delete_experiment_by_id(id=experiment.id)
    if not deleted_id:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"No experiment found with the id {experiment.id} for the collaborative experiment of the model {experiment.model_name} of the organization {experiment.organization_name}.",
        )

    deleted_exp = ExperimentPublic(**experiment.dict())
    return deleted_exp


@router.put(
    "/join",
    response_model=ExperimentJoinOutput,
    name="experiments:join-experiment-by-organization-and-model-name",
)
async def join_experiment_by_organization_and_model_name(
    organization_name: str,  # = Path(
    #     ..., ge=1, title="The name of the organization hosting the model that the user wants to collaboratively train."
    # ),
    model_name: str,  # = Path(..., ge=2, title="The name of the model that the user wants to collaboratively train."),
    experiment_join_input: ExperimentJoinInput = Body(..., embed=True),
    experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
    # whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
    # collaborators_repo: CollaboratorsRepository = Depends(get_repository(CollaboratorsRepository)),
    # users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
    user: MoonlandingUser = Depends(authenticate),
) -> ExperimentJoinOutput:
    experiment = await experiments_repo.get_experiment_by_organization_and_model_name(
        organization_name=organization_name, model_name=model_name
    )

    if experiment.organization_name not in [org.name for org in user.orgs]:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Access to the experiment denied.",
        )

    exp_pass = await join_experiment(experiment, user, experiment_join_input)
    return exp_pass


# @router.put("/join/{id}/", response_model=ExperimentJoinOutput, name="experiments:join-experiment-by-id")
# async def join_experiment_by_id(
#     id: int = Path(..., ge=1, title="The ID of the experiment the user wants to join."),
#     experiment_join_input: ExperimentJoinInput = Body(..., embed=True),
#     experiments_repo: ExperimentsRepository = Depends(get_repository(ExperimentsRepository)),
#     # whitelist_repo: WhitelistRepository = Depends(get_repository(WhitelistRepository)),
#     # collaborators_repo: CollaboratorsRepository = Depends(get_repository(CollaboratorsRepository)),
#     # users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
#     user: MoonlandingUser = Depends(authenticate),
# ) -> ExperimentJoinOutput:
#     experiment = await experiments_repo.get_experiment_by_id(id=id)

#     if not experiment:
#         raise HTTPException(
#             status_code=HTTP_401_UNAUTHORIZED,
#             detail="You need to be at least a reader of the organization to join the collaborative experiment for the model",
#         )

#     if experiment.organization_name not in [org.name for org in user.orgs]:
#         raise HTTPException(
#             status_code=HTTP_401_UNAUTHORIZED,
#             detail="Access to the experiment denied.",
#         )

#     exp_pass = await join_experiment(experiment, user, experiment_join_input)
#     return exp_pass


async def join_experiment(
    experiment: ExperimentInDB, user: MoonlandingUser, experiment_join_input: ExperimentJoinInput
):
    if not experiment:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No experiment found with that id.")

    hivemind_access = crypto.create_hivemind_access(
        peer_public_key=experiment_join_input.peer_public_key,
        auth_server_private_key=experiment.auth_server_private_key,
        username=user.username,
    )
    exp_pass = ExperimentJoinOutput(**experiment.dict(), hivemind_access=hivemind_access)
    return exp_pass


# TODO delete
# async def retrieve_full_experiment(
#     experiment_id: int,
#     # whitelist_repo: WhitelistRepository,
#     # collaborators_repo: CollaboratorsRepository,
#     # users_repo: UsersRepository,
#     experiment: ExperimentBase,
# ) -> ExperimentFullPublic:
#     all_experiment_id_items = await whitelist_repo.list_all_experiment_id_items(experiment_id=experiment_id)

#     collaborators = []
#     for whitelist_item in all_experiment_id_items:
#         user = await users_repo.get_user_by_id(id=whitelist_item.user_id)
#         collaborator_list = await collaborators_repo.list_all_collaborator_by_whitelist_item_id(
#             whitelist_item_id=whitelist_item.id
#         )
#         for collaborator in collaborator_list:
#             collaborators.append(
#                 CollaboratorPublic(
#                     username=user.username,
#                     peer_public_key=collaborator.peer_public_key,
#                     user_created_at=user.created_at,
#                     user_updated_at=user.updated_at,
#                     public_key_created_at=collaborator.created_at,
#                     public_key_updated_at=collaborator.updated_at,
#                 )
#             )
#         if collaborator_list == []:
#             collaborators.append(
#                 CollaboratorPublic(
#                     username=user.username,
#                     user_created_at=user.created_at,
#                     user_updated_at=user.updated_at,
#                 )
#             )

#     if collaborators != []:
#         experiment_full = ExperimentFullPublic(**experiment.dict(), collaborators=collaborators)
#     else:
#         experiment_full = ExperimentFullPublic(**experiment.dict())
#     return experiment_full


# async def remove_whitelist_item(
#     whitelist_item_id: int,
#     whitelist_repo: WhitelistRepository,
#     collaborators_repo: CollaboratorsRepository,
#     users_repo: UsersRepository,
# ):
#     user_ids = []
#     collaborators_ids = []

#     to_remove_item = await whitelist_repo.get_item_by_id(id=whitelist_item_id)

#     all_user_occurences_in_whitelist = await whitelist_repo.list_all_user_id_items(user_id=to_remove_item.user_id)

#     if len(all_user_occurences_in_whitelist) == 1:
#         user_ids.append(await users_repo.delete_user_by_id(id=to_remove_item.user_id))

#     collaborators_list = await collaborators_repo.list_all_collaborator_by_whitelist_item_id(
#         whitelist_item_id=whitelist_item_id
#     )
#     for collaborator in collaborators_list:
#         # raise ValueError(collaborator.id)
#         collaborators_ids.append(await collaborators_repo.delete_collaborator_by_id(id=collaborator.id))

#     whitelist_id = await whitelist_repo.delete_item_by_id(id=whitelist_item_id)

#     return (whitelist_id, user_ids, collaborators_ids)
