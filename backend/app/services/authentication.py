from functools import partial
from typing import Optional

import requests
from fastapi import Depends, HTTPException
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBase
from pydantic import BaseModel
from requests import ConnectionError, HTTPError
from starlette.status import HTTP_401_UNAUTHORIZED


HF_API = "https://huggingface.co/api"


class MoonlandingUser(BaseModel):
    """Dataclass holding a user info"""

    username: str
    email: Optional[str]


UnauthenticatedError = partial(
    HTTPException,
    status_code=HTTP_401_UNAUTHORIZED,
    headers={"WWW-Authenticate": 'Bearer realm="Access to the API"'},
)

api_key = HTTPBase(scheme="bearer", auto_error=False)


async def authenticate(credentials: Optional[HTTPAuthorizationCredentials] = Depends(api_key)) -> MoonlandingUser:
    if credentials is None:
        raise UnauthenticatedError(detail="Not authenticated")

    if credentials.scheme.lower() != "bearer":
        raise UnauthenticatedError(detail="Not authenticated")

    token = credentials.credentials
    try:
        user_identity = moonlanding_auth(token)
    except HTTPError as exc:
        if exc.response.status_code == 401:
            raise UnauthenticatedError(detail="Invalid credentials")
        else:
            raise UnauthenticatedError(detail="Error when authenticating")
    except ConnectionError:
        raise UnauthenticatedError(detail="Authentication backend could not be reached")

    username = user_identity["name"]
    email = user_identity["email"]

    # if user_identity["type"] == "user":
    #     is_org = False
    #     orgs = [org["name"] for org in user_identity["orgs"]]
    #     is_hf = "huggingface" in orgs
    #     is_autonlp = "autonlp" in orgs
    #     if not user_identity["emailVerified"]:
    #         raise HTTPException(
    #             status_code=HTTP_403_FORBIDDEN, detail="You need a verified email address to use AutoNLP"
    #         )
    # else:
    #     is_org = True
    #     orgs = []
    #     is_hf = username == "huggingface"
    #     is_autonlp = username == "autonlp"
    #     if not is_hf and (email is None or user_identity["plan"] == "NO_PLAN"):
    #         raise HTTPException(
    #             status_code=HTTP_403_FORBIDDEN,
    #             detail="You must suscribe to an organization plan to use AutoNLP as an organization: https://huggingface.co/pricing",
    #         )

    # # Prevent acces to staging to not HF users / orgs
    # if not (os.getenv("PRODUCTION") or is_hf or is_autonlp):
    #     raise HTTPException(status_code=HTTP_403_FORBIDDEN)

    return MoonlandingUser(username=username, email=email)


def moonlanding_auth(token: str) -> dict:
    """Validate token with Moon Landing
    TODO: cache requests to avoid flooding Moon Landing
    """
    auth_repsonse = requests.get(HF_API + "/whoami-v2", headers={"Authorization": f"Bearer {token}"}, timeout=3)
    auth_repsonse.raise_for_status()
    return auth_repsonse.json()


# def moonlanding_auth(token: str) -> dict:
#     """Validate token with Moon Landing
#     TODO: cache requests to avoid flooding Moon Landing
#     """
#     # auth_repsonse = requests.get(HF_API + "/whoami-v2", headers={"Authorization": f"Bearer {token}"}, timeout=3)
#     # auth_repsonse.raise_for_status()
#     return MoonlandingUser(username="User1", email="user1@test.co")
