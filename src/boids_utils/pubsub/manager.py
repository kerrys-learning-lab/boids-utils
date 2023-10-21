"""
Manages configured publisher and subscriber objects.
"""
import asyncio
import logging
import nats
from .exceptions import * # pylint: disable=wildcard-import
from .topic import * # pylint: disable=wildcard-import,unused-wildcard-import

LOGGER = logging.getLogger(__name__)

class PubsubTopicManager:
    """
    Manages configured publisher and subscriber objects.
    """

    def __init__(self) -> None:
        self.url = None
        self.nats_client = None
        self.client_id = None
        self._event = asyncio.Event()
        self._publishers: dict[str, TopicPublisher] = {}
        self._consumers: dict[str, TopicConsumer] = {}

    async def connect(self):
        """
        Connects to the NATS broker and begins processing publish/subscribe
        actions.
        """
        if self._event.is_set():
            return

        LOGGER.debug(f'Using NATS URL: {self.url}')
        self.nats_client = await nats.connect(self.url,
                                              error_cb=self._on_nats_error)
        LOGGER.info(f'Connected to NATS URL: {self.url}')

        for publisher in self._publishers.values():
            await publisher.on_connected(self.nats_client)


        for consumer in self._consumers.values():
            await consumer.on_connected(self.nats_client)
        self._event.set()

    async def disconnect(self):
        """
        Concludes processing of publish/subscribe actions and disconnects from the
        NATS broker.
        """
        if self.nats_client:
            for publisher in self._publishers.values():
                await publisher.disconnect()

            for consumer in self._consumers.values():
                await consumer.disconnect()

            await self.nats_client.drain()
            await self.nats_client.close()

        self.nats_client = None
        self._event.clear()


    def configure(self, pubsub_client_id: str, config: dict) -> None:
        """
        Applies the given 'pubsub' configuration.
        """
        self.url = config['url']
        self.client_id = pubsub_client_id
        nats_client_spec: dict = config.get('clients', {}).get(pubsub_client_id, {})

        producer_topics = nats_client_spec.get('publishes', [])
        consumer_topics = nats_client_spec.get('consumes', [])

        if not (producer_topics or consumer_topics):
            LOGGER.error(f'config: {config}')
            raise RuntimeError(f'Configuration must include "pubsub.url" and "pubsub.clients.{pubsub_client_id}" (or specify a different Pub/Sub client ID)')

        for topic_name in producer_topics:
            publisher: TopicPublisher = TopicPublisher(topic_name, pubsub_client_id)
            self._publishers[topic_name] = publisher
            LOGGER.debug(f'Created "{self.client_id}" publisher for topic "{topic_name}"')


        for topic_name in consumer_topics:
            consumer: TopicConsumer = TopicConsumer(topic_name, pubsub_client_id)
            self._consumers[topic_name] = consumer
            LOGGER.debug(f'Created "{self.client_id}" consumer for topic "{topic_name}"')

    def add_topic_callback(self, topic_name: str, callback: ConsumerCallback):
        """
        Registers the given callback for invocation upon receipt of messages on
        topic_name.  The topic must be configured as 'consumes' in the 'pubsub'
        configuration, else raises NoSuchTopicConsumer.

        Prerequisite: PubSubManager.configure
        """
        try:
            self._consumers[topic_name].add_listener(callback)
        except KeyError:
            # pylint: disable-next=raise-missing-from
            raise NoSuchTopicConsumer(f'No TopicConsumer for topic: {topic_name}')

    def get_topic_publisher(self, topic_name: str) -> TopicPublisher:
        """
        Returns a TopicPublisher for the given topic_name.  The topic must be configured
        as 'publishes' in the 'pubsub' configuration, else raises NoSuchTopicPublisher.

        All calls to this function with a given name return the same TopicPublisher
        instance. This means that publisher instances never need to be passed between
        different parts of an application.

        Prerequisite: PubsubTopicManager.configure
        """
        try:
            return self._publishers[topic_name]
        except KeyError:
            # pylint: disable-next=raise-missing-from
            raise NoSuchTopicPublisher(f'No TopicPublisher for topic: {topic_name}')

    async def _on_nats_error(self, error):
        LOGGER.error(f'Error: {error}')
