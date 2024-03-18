import asyncio
from datetime import UTC, datetime, timedelta
from pwd import getpwnam
from typing import Literal

import docker
import docker.errors
import docker.models.resource
from docker.utils import kwargs_from_env

from src import settings
from src.models import User

DOCKER_IMAGE = "ohdsi/broadsea-hades:4.2.1"


class Container:
    def __init__(self, user: User):
        self.client = docker.DockerClient(**kwargs_from_env())
        self.user = user
        self.container_name = f"hades-{self.user.username}"
        self.state: Literal[
            "restarting", "running", "paused", "exited", "uninititated"
        ] = "uninititated"
        self.internal_host: str = ""
        self.last_used: datetime = datetime.now(UTC)
        self.container = self.spawn()

        asyncio.create_task(self.poll())

    def spawn(self):
        try:
            container = self.client.containers.get(self.container_name)
        except docker.errors.NotFound:
            container = self.client.containers.run(
                image=DOCKER_IMAGE,
                name=self.container_name,
                environment={
                    "USER": self.user.username,
                    "PASSWORD": self.user.password,
                    "USERID": getpwnam(self.user.username).pw_uid,
                },
                volumes={
                    f"/home/{self.user.username}": {
                        "bind": f"/home/{self.user.username}",
                        "mode": "rw",
                    },
                },
                detach=True,
            )

        self.state = container.attrs["State"]["Status"]  # type: ignore
        if self.state == "paused":
            self.container.start()
        elif self.state == "exited":
            self.container.restart()

        self.internal_host = f"{self.get_internal_ip()}:{settings.HADES_PORT}"
        self.last_used = datetime.now(UTC)

        return container

    def get_internal_ip(self):
        return self.container.attrs["NetworkSettings"]["IPAddress"]  # type: ignore

    def update_last_used(self):
        self.last_used = datetime.now(UTC)

    async def poll(self):
        while True:
            await asyncio.sleep(30)

            self.container.reload()
            self.state = self.container.attrs["State"]["Status"]  # type: ignore
            self.internal_host = self.get_internal_ip()

            if self.last_used < datetime.now(UTC) - timedelta(hours=6):
                self.container.stop()
                self.state = "exited"
            
            print("Polling...")
