import asyncio
import logging
import pytest
import boids_utils.pubsub
import boids_utils.config

LOGGER = logging.getLogger(__name__)
TEST_TOPIC  = 'boids.test.topic'

class Consumer(boids_utils.pubsub.ConsumerCallback):
    def __init__(self) -> None:
       self._event = asyncio.Event()
       self.message = None

    def on_message(self, message: boids_utils.pubsub.Message):
        self.message = message
        self._event.set()

    async def wait(self):
       await self._event.wait()


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_topic_blocking(test_config):

    await boids_utils.pubsub.connect()

    listener = Consumer()
    boids_utils.pubsub.add_topic_callback(TEST_TOPIC, listener)

    sender: boids_utils.pubsub.TopicPublisher = boids_utils.pubsub.get_topic_publisher(TEST_TOPIC)

    LOGGER.debug(f'Sending message on topic: "{TEST_TOPIC}"')
    await sender.publish({'message': 'Foo'})

    await listener.wait()
    LOGGER.debug(f'Received message on topic: "{TEST_TOPIC}"')

    message = listener.message
    assert message.value['message'] == 'Foo'
    assert message.topic == TEST_TOPIC

    await boids_utils.pubsub.disconnect()
