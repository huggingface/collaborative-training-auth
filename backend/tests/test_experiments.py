import base64
import datetime
from ipaddress import IPv4Address, IPv6Address
from typing import List

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from app.api.dependencies import crypto
from app.models.experiment import ExperimentCreate
from app.models.experiment_full import ExperimentFullCreatePublic, ExperimentFullPublic, ExperimentFullUpdate
from app.models.experiment_join import ExperimentJoinInput, ExperimentJoinOutput
from app.models.user import UserCreate
from app.services.authentication import authenticate


# decorate all tests with @pytest.mark.asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
def new_experiment():
    return ExperimentFullCreatePublic(name="test experiment", collaborators=[UserCreate(username="peter")])


class TestExperimentsRoutes:
    async def test_routes_exist(self, app: FastAPI, client_wt_auth_user_1: AsyncClient) -> None:
        res = await client_wt_auth_user_1.post(app.url_path_for("experiments:create-experiment"), json={})
        assert res.status_code != status.HTTP_404_NOT_FOUND

    async def test_invalid_input_raises_error(self, app: FastAPI, client_wt_auth_user_1: AsyncClient) -> None:
        res = await client_wt_auth_user_1.post(app.url_path_for("experiments:create-experiment"), json={})
        assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCreateExperiment:
    @pytest.mark.parametrize(
        "new_experiment",
        (
            (ExperimentFullCreatePublic(name="test 2")),
            (ExperimentFullCreatePublic(name="test 3", collaborators=[UserCreate(username="peter")])),
            (
                ExperimentFullCreatePublic(
                    name="test 4", collaborators=[UserCreate(username="peter"), UserCreate(username="jane")]
                )
            ),
        ),
    )
    async def test_valid_input(
        self,
        app: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        moonlanding_user_1,
        new_experiment: dict,
    ) -> None:
        res = await client_wt_auth_user_1.post(
            app.url_path_for("experiments:create-experiment"),
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
        self, app: FastAPI, client_wt_auth_user_1: AsyncClient, invalid_payload: dict, status_code: int
    ) -> None:
        res = await client_wt_auth_user_1.post(
            app.url_path_for("experiments:create-experiment"), json={"new_experiment": invalid_payload}
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
        app: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        test_experiment_1_created_by_user_1: ExperimentFullPublic,
    ) -> None:
        res = await client_wt_auth_user_1.get(
            app.url_path_for("experiments:get-experiment-by-id", id=test_experiment_1_created_by_user_1.id)
        )
        assert res.status_code == status.HTTP_200_OK
        experiment = ExperimentFullPublic(**res.json())
        assert experiment == test_experiment_1_created_by_user_1

    async def test_get_experiment_by_id_unvalid_query_by_user_1(
        self,
        app: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        test_experiment_1_created_by_user_2: ExperimentFullPublic,
    ) -> None:
        res = await client_wt_auth_user_1.get(
            app.url_path_for("experiments:get-experiment-by-id", id=test_experiment_1_created_by_user_2.id)
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
        self, app: FastAPI, client_wt_auth_user_1: AsyncClient, id: int, status_code: int
    ) -> None:
        res = await client_wt_auth_user_1.get(app.url_path_for("experiments:get-experiment-by-id", id=id))
        assert res.status_code == status_code

    async def test_list_all_user_experiments_returns_valid_response(
        self,
        app: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        test_experiment_1_created_by_user_1: ExperimentFullPublic,
        test_experiment_2_created_by_user_1: ExperimentFullPublic,
    ) -> None:
        res = await client_wt_auth_user_1.get(app.url_path_for("experiments:list-all-user-experiments"))

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
            (
                ["collaborators"],
                ["added_collaborators"],
                [[UserCreate(username="User9").dict(), UserCreate(username="User1").dict()]],
            ),
            (
                ["collaborators"],
                ["removed_collaborators"],
                [[UserCreate(username="User3").dict(), UserCreate(username="user3").dict()]],
            ),
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
                    [UserCreate(username="User7").dict(), UserCreate(username="User8").dict()],
                    [UserCreate(username="User1").dict(), UserCreate(username="User2").dict()],
                ],
            ),
        ),
    )
    async def test_update_experiment_with_valid_input(
        self,
        app: FastAPI,
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
        res = await client_wt_auth_user_1.put(
            app.url_path_for("experiments:update-experiment-by-id", id=test_experiment_1_created_by_user_1.id),
            json=experiment_full_update,
        )
        assert res.status_code == status.HTTP_200_OK
        updated_experiment = ExperimentFullPublic(**res.json())
        assert updated_experiment.id == test_experiment_1_created_by_user_1.id  # make sure it's the same experiment

        # make sure that any attribute we updated has changed to the correct value
        for attr_to_change, update_key, value in zip(attrs_to_change, update_keys, values):
            # Beware, this can raise an error if someone ask to removed user not whitelisted (and it isn't an error)
            assert getattr(updated_experiment, attr_to_change) != getattr(
                test_experiment_1_created_by_user_1, attr_to_change
            )
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
        app: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        id: int,
        payload: dict,
        status_code: int,
    ) -> None:
        experiment_full_update = {"experiment_full_update": payload}
        res = await client_wt_auth_user_1.put(
            app.url_path_for("experiments:update-experiment-by-id", id=id),
            json=experiment_full_update,
        )
        assert res.status_code == status_code


class TestDeleteExperiment:
    async def test_can_delete_experiment_successfully(
        self,
        app: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        test_experiment_1_created_by_user_1: ExperimentFullPublic,
    ) -> None:
        # delete the experiment
        res = await client_wt_auth_user_1.delete(
            app.url_path_for("experiments:delete-experiment-by-id", id=test_experiment_1_created_by_user_1.id)
        )
        assert res.status_code == status.HTTP_200_OK
        # ensure that the experiment no longer exists
        res = await client_wt_auth_user_1.get(
            app.url_path_for("experiments:get-experiment-by-id", id=test_experiment_1_created_by_user_1.id)
        )
        assert res.status_code == status.HTTP_404_NOT_FOUND

    async def test_cant_delete_other_user_experiment(
        self,
        app: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        test_experiment_1_created_by_user_2: ExperimentFullPublic,
    ) -> None:
        # delete the experiment
        res = await client_wt_auth_user_1.delete(
            app.url_path_for("experiments:delete-experiment-by-id", id=test_experiment_1_created_by_user_2.id)
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
        moonlanding_user_1,
        app: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        test_experiment_1_created_by_user_1: ExperimentFullPublic,
        id: int,
        status_code: int,
    ) -> None:
        res = await client_wt_auth_user_1.delete(app.url_path_for("experiments:delete-experiment-by-id", id=id))
        assert res.status_code == status_code


class TestJoinExperiment:
    async def test_can_join_experiment_successfully(
        self,
        moonlanding_user_1,
        moonlanding_user_2,
        app: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        # client_wt_auth_user_2: AsyncClient,
        test_experiment_1_created_by_user_2: ExperimentFullPublic,
        test_experiment_join_input_1_by_user_1: ExperimentJoinInput,
        test_experiment_join_input_2_by_user_1: ExperimentJoinInput,
    ) -> None:
        values = test_experiment_join_input_1_by_user_1.dict()
        # Make the values JSON serializable
        values["peer_public_key"] = values["peer_public_key"].decode("utf-8")

        res = await client_wt_auth_user_1.put(
            app.url_path_for("experiments:join-experiment-by-id", id=test_experiment_1_created_by_user_2.id),
            json={"experiment_join_input": values},
        )
        assert res.status_code == status.HTTP_200_OK, res.content

        exp_pass = ExperimentJoinOutput(**res.json())
        assert getattr(exp_pass, "coordinator_ip") == test_experiment_1_created_by_user_2.coordinator_ip
        assert getattr(exp_pass, "coordinator_port") == test_experiment_1_created_by_user_2.coordinator_port

        hivemind_access = getattr(exp_pass, "hivemind_access")
        assert getattr(hivemind_access, "peer_public_key") == test_experiment_join_input_1_by_user_1.peer_public_key

        signature = base64.b64decode(getattr(hivemind_access, "signature"))

        auth_server_public_key = getattr(exp_pass, "auth_server_public_key")
        auth_server_public_key = crypto.load_public_key(auth_server_public_key)

        verif = auth_server_public_key.verify(
            signature,
            f"{hivemind_access.username} {hivemind_access.peer_public_key} {hivemind_access.expiration_time}".encode(),
            crypto.PADDING,
            crypto.HASH_ALGORITHM,
        )
        assert verif is None  # verify() returns None iff the signature is correct
        assert hivemind_access.expiration_time > datetime.datetime.utcnow()
        assert hivemind_access.username == moonlanding_user_1.username

        # Now the same user try to join a second time with another public key
        values = test_experiment_join_input_2_by_user_1.dict()
        # Make the values JSON serializable
        values["peer_public_key"] = values["peer_public_key"].decode("utf-8")

        res = await client_wt_auth_user_1.put(
            app.url_path_for("experiments:join-experiment-by-id", id=test_experiment_1_created_by_user_2.id),
            json={"experiment_join_input": values},
        )
        assert res.status_code == status.HTTP_200_OK, res.content

        exp_pass = ExperimentJoinOutput(**res.json())
        assert getattr(exp_pass, "coordinator_ip") == test_experiment_1_created_by_user_2.coordinator_ip
        assert getattr(exp_pass, "coordinator_port") == test_experiment_1_created_by_user_2.coordinator_port

        hivemind_access = getattr(exp_pass, "hivemind_access")
        assert getattr(hivemind_access, "peer_public_key") == test_experiment_join_input_2_by_user_1.peer_public_key

        signature = base64.b64decode(getattr(hivemind_access, "signature"))

        auth_server_public_key = getattr(exp_pass, "auth_server_public_key")
        auth_server_public_key = crypto.load_public_key(auth_server_public_key)

        verif = auth_server_public_key.verify(
            signature,
            f"{hivemind_access.username} {hivemind_access.peer_public_key} {hivemind_access.expiration_time}".encode(),
            crypto.PADDING,
            crypto.HASH_ALGORITHM,
        )
        assert verif is None  # verify() returns None iff the signature is correct
        assert hivemind_access.expiration_time > datetime.datetime.utcnow()
        assert hivemind_access.username == moonlanding_user_1.username

        # Verify if the 2 public keys have been saved in DB

        app.dependency_overrides[authenticate] = lambda: moonlanding_user_2

        res = await client_wt_auth_user_1.get(
            app.url_path_for("experiments:get-experiment-by-id", id=test_experiment_1_created_by_user_2.id)
        )
        assert res.status_code == status.HTTP_200_OK
        experiment = ExperimentFullPublic(**res.json())

        username_found = False
        public_key_1_found = False
        public_key_2_found = False

        collaborators_list = experiment.collaborators
        for collaborator in collaborators_list:
            if (
                collaborator.username == moonlanding_user_1.username
                and collaborator.peer_public_key == test_experiment_join_input_1_by_user_1.peer_public_key
            ):
                username_found = True
                public_key_1_found = True
            if (
                collaborator.username == moonlanding_user_1.username
                and collaborator.peer_public_key == test_experiment_join_input_2_by_user_1.peer_public_key
            ):
                username_found = True
                public_key_2_found = True

        assert username_found
        assert public_key_1_found
        assert public_key_2_found

    async def test_can_join_experiment_successfully_2_times_with_same_public_key(
        self,
        moonlanding_user_1,
        moonlanding_user_2,
        app: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        # client_wt_auth_user_2: AsyncClient,
        test_experiment_1_created_by_user_2: ExperimentFullPublic,
        test_experiment_join_input_1_by_user_1: ExperimentJoinInput,
    ) -> None:
        values = test_experiment_join_input_1_by_user_1.dict()
        # Make the values JSON serializable
        values["peer_public_key"] = values["peer_public_key"].decode("utf-8")

        res = await client_wt_auth_user_1.put(
            app.url_path_for("experiments:join-experiment-by-id", id=test_experiment_1_created_by_user_2.id),
            json={"experiment_join_input": values},
        )
        assert res.status_code == status.HTTP_200_OK, res.content

        exp_pass = ExperimentJoinOutput(**res.json())
        assert getattr(exp_pass, "coordinator_ip") == test_experiment_1_created_by_user_2.coordinator_ip
        assert getattr(exp_pass, "coordinator_port") == test_experiment_1_created_by_user_2.coordinator_port

        hivemind_access = getattr(exp_pass, "hivemind_access")
        assert getattr(hivemind_access, "peer_public_key") == test_experiment_join_input_1_by_user_1.peer_public_key

        signature = base64.b64decode(getattr(hivemind_access, "signature"))

        auth_server_public_key = getattr(exp_pass, "auth_server_public_key")
        auth_server_public_key = crypto.load_public_key(auth_server_public_key)

        verif = auth_server_public_key.verify(
            signature,
            f"{hivemind_access.username} {hivemind_access.peer_public_key} {hivemind_access.expiration_time}".encode(),
            crypto.PADDING,
            crypto.HASH_ALGORITHM,
        )
        assert verif is None  # verify() returns None iff the signature is correct
        assert hivemind_access.expiration_time > datetime.datetime.utcnow()
        assert hivemind_access.username == moonlanding_user_1.username

        # Now the same user try to join a second time with another public key
        values = test_experiment_join_input_1_by_user_1.dict()
        # Make the values JSON serializable
        values["peer_public_key"] = values["peer_public_key"].decode("utf-8")

        res = await client_wt_auth_user_1.put(
            app.url_path_for("experiments:join-experiment-by-id", id=test_experiment_1_created_by_user_2.id),
            json={"experiment_join_input": values},
        )
        assert res.status_code == status.HTTP_200_OK, res.content

        exp_pass = ExperimentJoinOutput(**res.json())
        assert getattr(exp_pass, "coordinator_ip") == test_experiment_1_created_by_user_2.coordinator_ip
        assert getattr(exp_pass, "coordinator_port") == test_experiment_1_created_by_user_2.coordinator_port

        hivemind_access = getattr(exp_pass, "hivemind_access")
        assert getattr(hivemind_access, "peer_public_key") == test_experiment_join_input_1_by_user_1.peer_public_key

        signature = base64.b64decode(getattr(hivemind_access, "signature"))

        auth_server_public_key = getattr(exp_pass, "auth_server_public_key")
        auth_server_public_key = crypto.load_public_key(auth_server_public_key)

        verif = auth_server_public_key.verify(
            signature,
            f"{hivemind_access.username} {hivemind_access.peer_public_key} {hivemind_access.expiration_time}".encode(),
            crypto.PADDING,
            crypto.HASH_ALGORITHM,
        )
        assert verif is None  # verify() returns None iff the signature is correct
        assert hivemind_access.expiration_time > datetime.datetime.utcnow()
        assert hivemind_access.username == moonlanding_user_1.username

        # Verify if the 2 public keys have been saved in DB

        app.dependency_overrides[authenticate] = lambda: moonlanding_user_2

        res = await client_wt_auth_user_1.get(
            app.url_path_for("experiments:get-experiment-by-id", id=test_experiment_1_created_by_user_2.id)
        )
        assert res.status_code == status.HTTP_200_OK
        experiment = ExperimentFullPublic(**res.json())

        username_found = False
        public_key_found = 0

        collaborators_list = experiment.collaborators
        for collaborator in collaborators_list:
            if (
                collaborator.username == moonlanding_user_1.username
                and collaborator.peer_public_key == test_experiment_join_input_1_by_user_1.peer_public_key
            ):
                username_found = True
                public_key_found += 1

        assert username_found
        assert public_key_found == 2

    async def test_cant_join_experiment_successfully_user_not_whitelisted(
        self,
        moonlanding_user_1,
        app: FastAPI,
        client_wt_auth_user_1: AsyncClient,
        test_experiment_2_created_by_user_2: ExperimentFullPublic,
        test_experiment_join_input_1_by_user_1: ExperimentJoinInput,
    ):
        values = test_experiment_join_input_1_by_user_1.dict()
        # Make the values JSON serializable
        values["peer_public_key"] = values["peer_public_key"].decode("utf-8")

        res = await client_wt_auth_user_1.put(
            app.url_path_for("experiments:join-experiment-by-id", id=test_experiment_2_created_by_user_2.id),
            json={"experiment_join_input": values},
        )
        assert res.status_code == status.HTTP_401_UNAUTHORIZED, res.content
