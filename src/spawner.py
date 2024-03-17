import docker
import docker.errors
from docker.utils import kwargs_from_env
from pwd import getpwnam


DOCKER_IMAGE = "ohdsi/broadsea-hades:4.2.1"


class Spawner:
    def __init__(self, user):
        self.client = docker.DockerClient(**kwargs_from_env())
        self.user = user
        self.container_name = f"hades-{self.user}"
        self.container = self.spawn()

    def spawn(self):
        try:
            container = self.client.containers.get(self.container_name)
        except docker.errors.NotFound:
            container = self.client.containers.run(
                DOCKER_IMAGE,
                name=self.container_name,
                environment={
                    "USER": self.user,
                    "PASSWORD": "password",
                    "USERID": getpwnam(self.user).pw_uid,
                },
                volumes={
                    f"/home/{self.user}": {
                        "bind": f"/home/{self.user}",
                        "mode": "rw",
                    },
                },
                detach=True,
            )
        return container

    def get_internal_ip(self):
        return self.container.attrs["NetworkSettings"]["IPAddress"]  # type: ignore
