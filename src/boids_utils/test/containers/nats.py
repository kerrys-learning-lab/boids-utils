''' NATS testcontainer implementation '''
import asyncio
import logging
import nats
import nats.errors

import testcontainers.core.container
import testcontainers.core.waiting_utils

LOGGER = logging.getLogger(__name__)

class NATSContainer(testcontainers.core.container.DockerContainer):
    """
    NATS container.

    Example:

        .. doctest::

            >>> from testcontainers.nats import NATSContainer

            >>> with NATSContainer() as NATS:
            ...    connection = NATS.get_server_url()
    """
    def __init__(self, image: str = "nats:2.9.23", port: int = 4222, **kwargs) -> None:
        super().__init__(image, **kwargs)
        self.port = port
        self.with_exposed_ports(self.port)

    def get_server_url(self) -> str:
        ''' Returns the URL to the NATS testcontainer.  The return value is
            suitable for use as-is by a client connection. '''
        host = self.get_container_host_ip()
        port = self.get_exposed_port(self.port)
        return f'nats://{host}:{port}'

    @testcontainers.core.waiting_utils.wait_container_is_ready(ValueError,
                                                               nats.errors.ConnectionClosedError,
                                                               nats.errors.TimeoutError,
                                                               nats.errors.NoServersError)
    def _connect(self) -> None:
        asyncio.run(nats.connect(self.get_server_url()))

    def start(self) -> "NATSContainer":
        """ Starts NATS, waits for the broker to be 'up' and returns the handle
            to the container """
        command = f'-p {self.port} --trace'
        self.with_command(command)
        super().start()
        self._connect()
        return self
