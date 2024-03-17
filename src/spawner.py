import docker
from docker.utils import kwargs_from_env
from pydantic import BaseModel


DOCKER_IMAGE = "ohdsi/broadsea-hades:4.2.1"


class Spawner:
    def __init__(self, user):
        self.client = docker.DockerClient(**kwargs_from_env())
        self.user = user
        self.container_name = f"hades-{self.user}"
        self.container = self.spawn()
        print(self.get_internal_ip())

    def spawn(self):
        container = self.client.containers.get(self.container_name)
        if not container:
            container = self.client.containers.run(
                DOCKER_IMAGE, name=self.container_name, detach=True
            )
        return container

    def get_internal_ip(self):
        return self.container.attrs["NetworkSettings"]["IPAddress"]  # type: ignore
