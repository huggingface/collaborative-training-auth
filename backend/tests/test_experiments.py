from ipaddress import IPv4Address, IPv6Address
from typing import List

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from app.models.experiment import ExperimentCreate
from app.models.experiment_full import ExperimentFullCreate, ExperimentFullPublic, ExperimentFullUpdate
from app.models.experiment_pass import ExperimentPassPublic
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
        "attrs_to_change, update_keys, values",
        (
            (["collaborators"], ["added_collaborators"], [[UserCreate(username="user9").dict()]]),
            (["collaborators"], ["removed_collaborators"], [[UserCreate(username="user99").dict()]]),
            (["coordinator_ip"], ["coordinator_ip"], ["192.0.2.0"]),
            (["coordinator_ip"], ["coordinator_ip"], ["684D:1111:222:3333:4444:5555:6:77"]),
            (["coordinator_port"], ["coordinator_port"], [400]),
            (
                [
                    "coordinator_ip",
                    "coordinator_port",
                    "collaborators",
                    "collaborators",
                ],
                [
                    "coordinator_ip",
                    "coordinator_port",
                    "added_collaborators",
                    "removed_collaborators",
                ],
                [
                    "00.00.00.00",
                    80,
                    [UserCreate(username="user7").dict(), UserCreate(username="user8").dict()],
                    [UserCreate(username="user10").dict(), UserCreate(username="user11").dict()],
                ],
            ),
        ),
    )
    async def test_update_experiment_with_valid_input(
        self,
        app_wt_auth_user_1: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        test_experiment_1_created_by_user_1: ExperimentFullPublic,
        attrs_to_change: List[str],
        update_keys: List[str],
        values: List[str],
    ) -> None:
        _ = ExperimentFullUpdate(**{update_keys[i]: values[i] for i in range(len(attrs_to_change))})
        experiment_full_update = {
            "experiment_full_update": {update_keys[i]: values[i] for i in range(len(attrs_to_change))}
        }
        # raise ValueError(experiment_full_update)
        res = await client_wt_auth_user_1.put(
            app_wt_auth_user_1.url_path_for(
                "experiments:update-experiment-by-id", id=test_experiment_1_created_by_user_1.id
            ),
            json=experiment_full_update,
        )
        assert res.status_code == status.HTTP_200_OK
        updated_experiment = ExperimentFullPublic(**res.json())
        assert updated_experiment.id == test_experiment_1_created_by_user_1.id  # make sure it's the same experiment

        # make sure that any attribute we updated has changed to the correct value
        for attr_to_change, update_key, value in zip(attrs_to_change, update_keys, values):
            # assert getattr(updated_experiment, attr_to_change) != getattr(
            #     test_experiment_1_created_by_user_1, attr_to_change
            # )
            if update_key == "added_collaborators":
                for collaborator_to_add in value:
                    assert collaborator_to_add in [
                        UserCreate(**collaborator.dict()).dict()
                        for collaborator in getattr(updated_experiment, attr_to_change)
                    ]
            elif update_key == "removed_collaborators":
                for collaborator_to_remove in value:
                    assert collaborator_to_remove not in [
                        UserCreate(**collaborator.dict()).dict()
                        for collaborator in getattr(updated_experiment, attr_to_change)
                    ]
            else:
                final_value = getattr(updated_experiment, attr_to_change)
                if isinstance(final_value, IPv4Address):
                    assert final_value == IPv4Address(value)
                elif isinstance(final_value, IPv6Address):
                    assert final_value == IPv6Address(value)
                else:
                    assert final_value == value

        # make sure that no other attributes' values have changed
        for attr, value in updated_experiment.dict().items():
            if attr not in attrs_to_change and attr != "updated_at":
                final_value = getattr(test_experiment_1_created_by_user_1, attr)

                if isinstance(final_value, IPv4Address):
                    assert final_value == IPv4Address(value)
                elif isinstance(final_value, IPv6Address):
                    assert final_value == IPv6Address(value)
                else:
                    assert final_value == value
            if attr == "updated_at":
                assert getattr(test_experiment_1_created_by_user_1, attr) != value

    @pytest.mark.parametrize(
        "id, payload, status_code",
        (
            (-1, {"name": "test"}, 422),
            (0, {"name": "test2"}, 422),
            (500, {}, 404),
            (500, {"name": "test3"}, 404),
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
        experiment_full_update = {"experiment_full_update": payload}
        res = await client_wt_auth_user_1.put(
            app_wt_auth_user_1.url_path_for("experiments:update-experiment-by-id", id=id),
            json=experiment_full_update,
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


class TestJoinExperiment:
    async def test_can_join_experiment_successfully(
        self,
        app_wt_auth_user_1: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        test_experiment_created_by_user_2: ExperimentFullPublic,
    ) -> None:
        res = await client_wt_auth_user_1.put(
            app_wt_auth_user_1.url_path_for(
                "experiments:join-experiment-by-id", id=test_experiment_created_by_user_2.id
            )
        )
        assert res.status_code == status.HTTP_200_OK, res.content
        exp_pass = ExperimentPassPublic(**res.json())
        assert getattr(exp_pass, "coordinator_ip") == test_experiment_created_by_user_2.coordinator_ip
        assert getattr(exp_pass, "coordinator_port") == test_experiment_created_by_user_2.coordinator_port

    async def test_cant_join_experiment_successfully(self):
        pass
