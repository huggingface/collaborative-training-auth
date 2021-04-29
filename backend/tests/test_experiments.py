from typing import List

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from app.models.experiment import ExperimentCreate
from app.models.experiment_full import ExperimentFullCreate, ExperimentFullPublic
from app.models.user import UserCreate


# decorate all tests with @pytest.mark.asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
def new_experiment():
    return ExperimentFullCreate(name="test experiment", collaborators=[UserCreate(username="peter")])


class TestExperimentsRoutes:
    async def test_routes_exist(self, app_wt_auth_user_1: FastAPI, client_wt_auth_user_1: AsyncClient) -> None:
        res = await client_wt_auth_user_1.post(
            app_wt_auth_user_1.url_path_for("experiments:create-experiment"), json={}
        )
        assert res.status_code != status.HTTP_404_NOT_FOUND

    async def test_invalid_input_raises_error(
        self, app_wt_auth_user_1: FastAPI, client_wt_auth_user_1: AsyncClient
    ) -> None:
        res = await client_wt_auth_user_1.post(
            app_wt_auth_user_1.url_path_for("experiments:create-experiment"), json={}
        )
        assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCreateExperiment:
    @pytest.mark.parametrize(
        "new_experiment",
        (
            (ExperimentFullCreate(name="test 2")),
            (ExperimentFullCreate(name="test 3", collaborators=[UserCreate(username="peter")])),
            (
                ExperimentFullCreate(
                    name="test 4", collaborators=[UserCreate(username="peter"), UserCreate(username="jane")]
                )
            ),
        ),
    )
    async def test_valid_input(
        self,
        app_wt_auth_user_1: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        moonlanding_user_1,
        new_experiment: dict,
    ) -> None:
        res = await client_wt_auth_user_1.post(
            app_wt_auth_user_1.url_path_for("experiments:create-experiment"),
            json={"new_experiment": new_experiment.dict()},
        )
        assert res.status_code == status.HTTP_201_CREATED

        created_experiment = ExperimentFullPublic(**res.json())
        assert created_experiment.name == new_experiment.name
        assert created_experiment.owner == moonlanding_user_1.username

        if new_experiment.collaborators:
            username_list_init = [collaborator.username for collaborator in new_experiment.collaborators]
            username_list_final = [collaborator.username for collaborator in created_experiment.collaborators]
            assert username_list_final == username_list_init

    @pytest.mark.parametrize(
        "invalid_payload, status_code",
        (
            (None, 422),
            ({}, 422),
        ),
    )
    async def test_invalid_input_raises_error(
        self, app_wt_auth_user_1: FastAPI, client_wt_auth_user_1: AsyncClient, invalid_payload: dict, status_code: int
    ) -> None:
        res = await client_wt_auth_user_1.post(
            app_wt_auth_user_1.url_path_for("experiments:create-experiment"), json={"new_experiment": invalid_payload}
        )
        assert res.status_code == status_code

    async def test_unauthenticated_user_unable_to_create_experiment(
        self, app: FastAPI, client: AsyncClient, new_experiment: ExperimentCreate
    ) -> None:
        res = await client.post(
            app.url_path_for("experiments:create-experiment"),
            json={"new_experiment": new_experiment.dict()},
        )
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetExperiment:
    async def test_get_experiment_by_id_valid_query_by_user_1(
        self,
        app_wt_auth_user_1: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        test_experiment_1_created_by_user_1: ExperimentFullPublic,
    ) -> None:
        res = await client_wt_auth_user_1.get(
            app_wt_auth_user_1.url_path_for(
                "experiments:get-experiment-by-id", id=test_experiment_1_created_by_user_1.id
            )
        )
        assert res.status_code == status.HTTP_200_OK
        experiment = ExperimentFullPublic(**res.json())
        assert experiment == test_experiment_1_created_by_user_1

    async def test_get_experiment_by_id_unvalid_query_by_user_1(
        self,
        app_wt_auth_user_1: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        test_experiment_created_by_user_2: ExperimentFullPublic,
    ) -> None:
        res = await client_wt_auth_user_1.get(
            app_wt_auth_user_1.url_path_for(
                "experiments:get-experiment-by-id", id=test_experiment_created_by_user_2.id
            )
        )
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "id, status_code",
        (
            (500, 404),
            (-1, 404),
            (None, 422),
        ),
    )
    async def test_wrong_id_returns_error(
        self, app_wt_auth_user_1: FastAPI, client_wt_auth_user_1: AsyncClient, id: int, status_code: int
    ) -> None:
        res = await client_wt_auth_user_1.get(
            app_wt_auth_user_1.url_path_for("experiments:get-experiment-by-id", id=id)
        )
        assert res.status_code == status_code

    async def test_list_all_user_experiments_returns_valid_response(
        self,
        app_wt_auth_user_1: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        test_experiment_1_created_by_user_1: ExperimentFullPublic,
        test_experiment_2_created_by_user_1: ExperimentFullPublic,
    ) -> None:
        res = await client_wt_auth_user_1.get(app_wt_auth_user_1.url_path_for("experiments:list-all-user-experiments"))

        assert res.status_code == status.HTTP_200_OK
        assert isinstance(res.json(), list)
        assert len(res.json()) > 0
        experiments = [ExperimentFullPublic(**exp) for exp in res.json()]
        assert test_experiment_1_created_by_user_1 in experiments
        assert test_experiment_2_created_by_user_1 in experiments


class TestUpdateExperiment:
    @pytest.mark.parametrize(
        "attrs_to_change, values",
        (
            (["collaborators"], [[UserCreate(username="user7").dict(), UserCreate(username="user8").dict()]]),
            (["collaborators"], [[UserCreate(username="user9").dict()]]),
        ),
    )
    async def test_update_experiment_with_valid_input(
        self,
        app_wt_auth_user_1: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        test_experiment_1_created_by_user_1: ExperimentFullPublic,
        attrs_to_change: List[str],
        values: List[str],
    ) -> None:
        experiment_update = {"experiment_update": {attrs_to_change[i]: values[i] for i in range(len(attrs_to_change))}}
        res = await client_wt_auth_user_1.put(
            app_wt_auth_user_1.url_path_for(
                "experiments:add-new-collaborators-to-experiment", id=test_experiment_1_created_by_user_1.id
            ),
            json=experiment_update,
        )
        assert res.status_code == status.HTTP_200_OK
        updated_experiment = ExperimentFullPublic(**res.json())
        assert updated_experiment.id == test_experiment_1_created_by_user_1.id  # make sure it's the same experiment

        # make sure that any attribute we updated has changed to the correct value
        for i in range(len(attrs_to_change)):
            assert getattr(updated_experiment, attrs_to_change[i]) != getattr(
                test_experiment_1_created_by_user_1, attrs_to_change[i]
            )
            for collaborator_to_add in values[i]:
                assert collaborator_to_add in [
                    UserCreate(**collaborator.dict()).dict()
                    for collaborator in getattr(updated_experiment, attrs_to_change[i])
                ]
        # make sure that no other attributes' values have changed
        for attr, value in updated_experiment.dict().items():
            if attr not in attrs_to_change:
                assert getattr(test_experiment_1_created_by_user_1, attr) == value

    @pytest.mark.parametrize(
        "id, payload, status_code",
        (
            (-1, {"name": "test"}, 422),
            (0, {"name": "test2"}, 422),
            (500, {"name": "test3"}, 404),
            (1, None, 422),
        ),
    )
    async def test_update_experiment_with_invalid_input_throws_error(
        self,
        app_wt_auth_user_1: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        id: int,
        payload: dict,
        status_code: int,
    ) -> None:
        experiment_update = {"experiment_update": payload}
        res = await client_wt_auth_user_1.put(
            app_wt_auth_user_1.url_path_for("experiments:add-new-collaborators-to-experiment", id=id),
            json=experiment_update,
        )
        assert res.status_code == status_code


class TestDeleteExperiment:
    async def test_can_delete_experiment_successfully(
        self,
        app_wt_auth_user_1: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        test_experiment_1_created_by_user_1: ExperimentFullPublic,
    ) -> None:
        # delete the experiment
        res = await client_wt_auth_user_1.delete(
            app_wt_auth_user_1.url_path_for(
                "experiments:delete-experiment-by-id", id=test_experiment_1_created_by_user_1.id
            )
        )
        assert res.status_code == status.HTTP_200_OK
        # ensure that the experiment no longer exists
        res = await client_wt_auth_user_1.get(
            app_wt_auth_user_1.url_path_for(
                "experiments:get-experiment-by-id", id=test_experiment_1_created_by_user_1.id
            )
        )
        assert res.status_code == status.HTTP_404_NOT_FOUND

    async def test_cant_delete_other_user_experiment(
        self,
        app_wt_auth_user_1: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        test_experiment_created_by_user_2: ExperimentFullPublic,
    ) -> None:
        # delete the experiment
        res = await client_wt_auth_user_1.delete(
            app_wt_auth_user_1.url_path_for(
                "experiments:delete-experiment-by-id", id=test_experiment_created_by_user_2.id
            )
        )
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "id, status_code",
        (
            (500, 404),
            (0, 422),
            (-1, 422),
            (None, 422),
        ),
    )
    async def test_can_delete_experiment_unsuccessfully(
        self,
        app_wt_auth_user_1: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        test_experiment_1_created_by_user_1: ExperimentFullPublic,
        id: int,
        status_code: int,
    ) -> None:
        res = await client_wt_auth_user_1.delete(
            app_wt_auth_user_1.url_path_for("experiments:delete-experiment-by-id", id=id)
        )
        assert res.status_code == status_code
