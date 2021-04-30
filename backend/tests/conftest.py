import os
import warnings

import alembic
import pytest
from alembic.config import Config
from asgi_lifespan import LifespanManager
from databases import Database
from fastapi import FastAPI
from httpx import AsyncClient

from app.api.routes.experiments import create_new_experiment, update_experiment_by_id
from app.db.repositories.experiments import ExperimentsRepository
from app.db.repositories.users import UsersRepository
from app.db.repositories.whitelist import WhitelistRepository
from app.models.experiment_full import ExperimentFullCreate, ExperimentFullPublic, ExperimentFullUpdate
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


# Fixtures for authenticated user 1

# Create a user for testing
@pytest.fixture
def moonlanding_user_1() -> MoonlandingUser:
    moonlanding_user_1 = MoonlandingUser(username="User1", email="user1@test.co")
    return moonlanding_user_1


# Create a new application for testing
@pytest.fixture
def app_wt_auth_user_1(apply_migrations: None, moonlanding_user_1: MoonlandingUser) -> FastAPI:
    from app.api.server import get_application
    from app.services.authentication import authenticate

    app = get_application()

    app.dependency_overrides[authenticate] = lambda: moonlanding_user_1

    return app


# Grab a reference to our database when needed
@pytest.fixture
def db_wt_auth_user_1(app_wt_auth_user_1: FastAPI) -> Database:
    return app_wt_auth_user_1.state._db


# Make requests in our tests
@pytest.fixture
async def client_wt_auth_user_1(app_wt_auth_user_1: FastAPI) -> AsyncClient:
    async with LifespanManager(app_wt_auth_user_1):
        async with AsyncClient(
            app=app_wt_auth_user_1, base_url="http://testserver", headers={"Content-Type": "application/json"}
        ) as client:
            yield client


@pytest.fixture
async def test_experiment_1_created_by_user_1(
    db_wt_auth_user_1: Database, moonlanding_user_1: MoonlandingUser
) -> ExperimentFullPublic:
    experiments_repo = ExperimentsRepository(db_wt_auth_user_1)
    users_repo = UsersRepository(db_wt_auth_user_1)
    whitelist_repo = WhitelistRepository(db_wt_auth_user_1)

    new_experiment = ExperimentFullCreate(
        name="fake experiment 1 created by user 1 name",
        collaborators=[
            UserCreate(username="user1"),
            UserCreate(username="user2"),
            UserCreate(username="user3"),
            UserCreate(username="user10"),
            UserCreate(username="user11"),
        ],
    )
    new_exp = await create_new_experiment(
        new_experiment=new_experiment,
        experiments_repo=experiments_repo,
        users_repo=users_repo,
        whitelist_repo=whitelist_repo,
        user=moonlanding_user_1,
    )
    return new_exp


@pytest.fixture
async def test_experiment_2_created_by_user_1(
    db_wt_auth_user_1: Database, moonlanding_user_1: MoonlandingUser
) -> ExperimentFullPublic:
    experiments_repo = ExperimentsRepository(db_wt_auth_user_1)
    users_repo = UsersRepository(db_wt_auth_user_1)
    whitelist_repo = WhitelistRepository(db_wt_auth_user_1)

    new_experiment = ExperimentFullCreate(
        name="fake experiment 2 created by user 1 name",
        collaborators=[UserCreate(username="user1"), UserCreate(username="user4"), UserCreate(username="user5")],
    )
    return await create_new_experiment(
        new_experiment=new_experiment,
        experiments_repo=experiments_repo,
        users_repo=users_repo,
        whitelist_repo=whitelist_repo,
        user=moonlanding_user_1,
    )


# Fixtures for authenticated user 2

# Create a user for testing
@pytest.fixture
def moonlanding_user_2() -> MoonlandingUser:
    moonlanding_user_2 = MoonlandingUser(username="User2", email="user2@test.co")
    return moonlanding_user_2


@pytest.fixture
async def test_experiment_created_by_user_2(
    db_wt_auth_user_1: Database, moonlanding_user_2: MoonlandingUser
) -> ExperimentFullPublic:
    experiments_repo = ExperimentsRepository(db_wt_auth_user_1)
    users_repo = UsersRepository(db_wt_auth_user_1)
    whitelist_repo = WhitelistRepository(db_wt_auth_user_1)

    new_experiment = ExperimentFullCreate(
        name="fake experiment 1 created by user 2 name",
        collaborators=[UserCreate(username="user1"), UserCreate(username="user4"), UserCreate(username="user6")],
    )
    experiment = await create_new_experiment(
        new_experiment=new_experiment,
        experiments_repo=experiments_repo,
        users_repo=users_repo,
        whitelist_repo=whitelist_repo,
        user=moonlanding_user_2,
    )
    exp = await update_experiment_by_id(
        id=experiment.id,
        experiment_full_update=ExperimentFullUpdate(coordinator_ip="192.0.2.0", coordinator_port=80),
        experiments_repo=experiments_repo,
        users_repo=users_repo,
        whitelist_repo=whitelist_repo,
        user=moonlanding_user_2,
    )
    return exp
