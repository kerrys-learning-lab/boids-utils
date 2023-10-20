"""
Provides publishing and subscribing classes.
"""
import abc
import logging
import dataclasses
import nats
import nats.aio.client
import boids_utils

LOGGER = logging.getLogger(__name__)

@dataclasses.dataclass
class Message:
    """
    A message received from the broker.
    """
    topic: str = None
    value: dict = None
    headers: dict[str, str] = None


class ConsumerCallback(abc.ABC):
    """ Base-class for asynchronous callbacks on received messages. """

    @abc.abstractmethod
    def on_message(self, message: Message):
        """ Called upon receipt of a message on a topic """

class TopicPublisher:
    """ TopicPublishers should NEVER be instantiated directly, but always
        retrieved through the module-level function
        pubsub.get_topic_publisher(topic_name). Multiple calls to
        pubsub.get_topic_publisher() with the same topic_name will always return
        a reference to the same TopicPublisher object. """

    def __init__(self,
                 topic_name: str,
                 client_id: str,
                 connection: nats.NATS = None) -> None:
        self.topic = topic_name
        self.client_id = client_id
        if connection:
            self.on_connected(connection)
        else:
            self.connection = None

    async def on_connected(self, connection: nats.NATS):
        """ Called by the pubsub module when a connection to the NATS broker
            is established. """
        self.connection = connection

    async def disconnect(self):
        """ Called by the pubsub module when the connection to the NATS broker
            is being terminated. """
        self.connection = None

    async def publish(self, value: dict, headers: dict[str,str] = None):
        """ Publishes a message on this TopicPublisher's topic.

            NOTE: 'value' is assumed to be a JSON-serializable object """
        if not self.connection:
            raise RuntimeError(f'Cannot publish to topic {self.topic} (not connected).')

        await self.connection.publish(self.topic,
                                      payload = boids_utils.Serde.serialize_json_value(value),
                                      headers = headers)


class TopicConsumer:
    """ TopicConsumers should NEVER be instantiated directly.  Instead, register
        a ConsumerCallback thru pubsub.add_topic_callback(...). """

    def __init__(self,
                 topic_name: str,
                 client_id: str,
                 connection: nats.NATS = None) -> None:
        self.topic = topic_name
        self.client_id = client_id
        self._listeners: list[ConsumerCallback] = []
        self._subscription = None

        if connection:
            self.on_connected(connection)
        else:
            self.connection = None

    async def on_connected(self, connection: nats.NATS):
        """ Called by the pubsub module when a connection to the NATS broker
            is established. """
        self.connection = connection

        if not self._listeners:
            LOGGER.warning(f'Subscribing to topic "{self.topic}" with no registered listeners.')

        if not self._subscription:
            self._subscription = await self.connection.subscribe(self.topic,
                                                                 self.client_id,
                                                                 cb=self.on_message)

    async def disconnect(self):
        """ Called by the pubsub module when the connection to the NATS broker
            is being terminated. """
        if self._subscription:
            await self._subscription.unsubscribe()
        self.connection = None
        self._subscription = None

    def add_listener(self, listener: ConsumerCallback):
        """ Called by the pubsub module when a ConsumerCallback is to be
            registered for this TopicConsumer's topic. """
        self._listeners.append(listener)

        if self.connection:
            LOGGER.warning(f'Registering a listener to "{self.topic}" after connection may result in data loss.')

    async def on_message(self, msg: nats.aio.client.Msg):
        """ Called by the pubsub module when a message is received on this
            TopicConsumer's topic. """
        message = Message(topic=self.topic,
                          value=boids_utils.Serde.deserialize_json_value(msg.data),
                          headers=msg.headers)

        for listener in self._listeners:
            try:
                listener.on_message(message)
            except Exception as ex: # pylint: disable=broad-except
                LOGGER.error(f'Uncaught exception in topic "{self.topic} listener: {ex}')
