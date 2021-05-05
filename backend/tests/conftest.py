import os
import warnings

import alembic
import pytest
from alembic.config import Config
from asgi_lifespan import LifespanManager
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from databases import Database
from fastapi import FastAPI
from httpx import AsyncClient

from app.api.routes.experiments import create_new_experiment, update_experiment_by_id
from app.db.repositories.collaborators import CollaboratorsRepository
from app.db.repositories.experiments import ExperimentsRepository
from app.db.repositories.users import UsersRepository
from app.db.repositories.whitelist import WhitelistRepository
from app.models.experiment_full import ExperimentFullCreatePublic, ExperimentFullPublic, ExperimentFullUpdate
from app.models.experiment_join import ExperimentJoinInput
from app.models.user import UserCreate
from app.services.authentication import MoonlandingUser


# Apply migrations at beginning and end of testing session
@pytest.fixture(scope="session")
def apply_migrations():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    os.environ["TESTING"] = "1"
    config = Config("alembic.ini")
    alembic.command.upgrade(config, "head")
    yield
    alembic.command.downgrade(config, "base")


# Create a new application for testing
@pytest.fixture
def app(apply_migrations: None) -> FastAPI:
    from app.api.server import get_application

    app = get_application()

    return app


# Grab a reference to our database when needed
@pytest.fixture
def db(app: FastAPI) -> Database:
    return app.state._db


# Make requests in our tests
@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    async with LifespanManager(app):
        async with AsyncClient(
            app=app, base_url="http://testserver", headers={"Content-Type": "application/json"}
        ) as client:
            yield client


# Fixtures for authenticated User1

# Create a user for testing
@pytest.fixture
def moonlanding_user_1() -> MoonlandingUser:
    moonlanding_user_1 = MoonlandingUser(username="User1", email="user1@test.co")
    return moonlanding_user_1


# Make requests in our tests
@pytest.fixture
async def client_wt_auth_user_1(app: FastAPI, moonlanding_user_1: MoonlandingUser) -> AsyncClient:
    from app.services.authentication import authenticate

    app.dependency_overrides[authenticate] = lambda: moonlanding_user_1
    async with LifespanManager(app):
        async with AsyncClient(
            app=app, base_url="http://testserver", headers={"Content-Type": "application/json"}
        ) as client:
            yield client


@pytest.fixture
async def test_experiment_1_created_by_user_1(
    db: Database, moonlanding_user_1: MoonlandingUser
) -> ExperimentFullPublic:
    experiments_repo = ExperimentsRepository(db)
    users_repo = UsersRepository(db)
    whitelist_repo = WhitelistRepository(db)
    collaborators_repo = CollaboratorsRepository(db)

    new_experiment = ExperimentFullCreatePublic(
        name="fake experiment 1 created by User1 name",
        collaborators=[
            UserCreate(username="User1"),
            UserCreate(username="User2"),
            UserCreate(username="User3"),
            UserCreate(username="User10"),
            UserCreate(username="User11"),
        ],
    )
    new_exp = await create_new_experiment(
        new_experiment=new_experiment,
        experiments_repo=experiments_repo,
        users_repo=users_repo,
        whitelist_repo=whitelist_repo,
        collaborators_repo=collaborators_repo,
        user=moonlanding_user_1,
    )
    return new_exp


@pytest.fixture
async def test_experiment_2_created_by_user_1(
    db: Database, moonlanding_user_1: MoonlandingUser
) -> ExperimentFullPublic:
    experiments_repo = ExperimentsRepository(db)
    users_repo = UsersRepository(db)
    whitelist_repo = WhitelistRepository(db)
    collaborators_repo = CollaboratorsRepository(db)

    new_experiment = ExperimentFullCreatePublic(
        name="fake experiment 2 created by User1 name",
        collaborators=[UserCreate(username="User1"), UserCreate(username="User4"), UserCreate(username="User5")],
    )
    return await create_new_experiment(
        new_experiment=new_experiment,
        experiments_repo=experiments_repo,
        users_repo=users_repo,
        whitelist_repo=whitelist_repo,
        collaborators_repo=collaborators_repo,
        user=moonlanding_user_1,
    )


@pytest.fixture
async def test_experiment_join_input_1_by_user_1() -> ExperimentJoinInput:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    serialized_public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH, format=serialization.PublicFormat.OpenSSH
    )
    return ExperimentJoinInput(peer_public_key=serialized_public_key)


@pytest.fixture
async def test_experiment_join_input_2_by_user_1() -> ExperimentJoinInput:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    serialized_public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH, format=serialization.PublicFormat.OpenSSH
    )
    return ExperimentJoinInput(peer_public_key=serialized_public_key)


# Fixtures for authenticated User2

# Create a user for testing
@pytest.fixture
def moonlanding_user_2() -> MoonlandingUser:
    moonlanding_user_2 = MoonlandingUser(username="User2", email="user2@test.co")
    return moonlanding_user_2


@pytest.fixture
async def client_wt_auth_user_2(app: FastAPI, moonlanding_user_2: MoonlandingUser) -> AsyncClient:
    from app.services.authentication import authenticate

    app.dependency_overrides[authenticate] = lambda: moonlanding_user_2
    async with LifespanManager(app):
        async with AsyncClient(
            app=app, base_url="http://testserver", headers={"Content-Type": "application/json"}
        ) as client:
            yield client


@pytest.fixture
async def test_experiment_1_created_by_user_2(
    db: Database, moonlanding_user_2: MoonlandingUser
) -> ExperimentFullPublic:
    experiments_repo = ExperimentsRepository(db)
    users_repo = UsersRepository(db)
    whitelist_repo = WhitelistRepository(db)
    collaborators_repo = CollaboratorsRepository(db)

    new_experiment = ExperimentFullCreatePublic(
        name="fake experiment 1 created by User2 name",
        collaborators=[UserCreate(username="User1"), UserCreate(username="User4"), UserCreate(username="User6")],
    )
    experiment = await create_new_experiment(
        new_experiment=new_experiment,
        experiments_repo=experiments_repo,
        users_repo=users_repo,
        whitelist_repo=whitelist_repo,
        collaborators_repo=collaborators_repo,
        user=moonlanding_user_2,
    )
    exp = await update_experiment_by_id(
        id=experiment.id,
        experiment_full_update=ExperimentFullUpdate(coordinator_ip="192.0.2.0", coordinator_port=80),
        experiments_repo=experiments_repo,
        users_repo=users_repo,
        whitelist_repo=whitelist_repo,
        collaborators_repo=collaborators_repo,
        user=moonlanding_user_2,
    )
    return exp


@pytest.fixture
async def test_experiment_2_created_by_user_2(
    db: Database, moonlanding_user_2: MoonlandingUser
) -> ExperimentFullPublic:
    experiments_repo = ExperimentsRepository(db)
    users_repo = UsersRepository(db)
    whitelist_repo = WhitelistRepository(db)
    collaborators_repo = CollaboratorsRepository(db)

    new_experiment = ExperimentFullCreatePublic(
        name="fake experiment 1 created by User2 name",
        collaborators=[UserCreate(username="user1"), UserCreate(username="User4"), UserCreate(username="User6")],
    )
    experiment = await create_new_experiment(
        new_experiment=new_experiment,
        experiments_repo=experiments_repo,
        users_repo=users_repo,
        whitelist_repo=whitelist_repo,
        collaborators_repo=collaborators_repo,
        user=moonlanding_user_2,
    )
    exp = await update_experiment_by_id(
        id=experiment.id,
        experiment_full_update=ExperimentFullUpdate(coordinator_ip="192.0.2.0", coordinator_port=80),
        experiments_repo=experiments_repo,
        users_repo=users_repo,
        whitelist_repo=whitelist_repo,
        collaborators_repo=collaborators_repo,
        user=moonlanding_user_2,
    )
    return exp
