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
from typing import Optional

from pydantic import IPvAnyAddress, validator

from app.models.core import CoreModel, DateTimeModelMixin, IDModelMixin


class ExperimentBase(CoreModel):
    """
    All common characteristics of our Experiment resource
    """

    name: Optional[str]
    coordinator_ip: Optional[IPvAnyAddress]
    coordinator_port: Optional[int]

    @validator("coordinator_port")
    def validate_port(cls, port):
        if port is None:
            return port

        if int(port) > 2 ** 16:
            raise ValueError("port overflow")
        return port


class ExperimentCreatePublic(ExperimentBase):
    name: str


class ExperimentCreate(ExperimentBase):
    name: str
    auth_server_public_key: Optional[bytes]
    auth_server_private_key: Optional[bytes]


class ExperimentUpdate(ExperimentBase):
    pass


class ExperimentInDB(IDModelMixin, DateTimeModelMixin, ExperimentBase):
    name: str
    owner: str
    auth_server_public_key: Optional[bytes]
    auth_server_private_key: Optional[bytes]


class ExperimentPublic(IDModelMixin, DateTimeModelMixin, ExperimentBase):
    owner: str
