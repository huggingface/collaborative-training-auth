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

    return MoonlandingUser(username=username, email=email)


def moonlanding_auth(token: str) -> dict:
    """Validate token with Moon Landing
    TODO: cache requests to avoid flooding Moon Landing
    """
    auth_repsonse = requests.get(HF_API + "/whoami-v2", headers={"Authorization": f"Bearer {token}"}, timeout=3)
    auth_repsonse.raise_for_status()
    return auth_repsonse.json()
