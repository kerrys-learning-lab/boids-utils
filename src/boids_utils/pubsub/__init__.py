"""
Configures the pubsub module using command-line arguments and dict/yaml
values.
"""
import argparse
from .exceptions import *
from .manager import *
from .topic import *


TOPIC_MANAGER = PubsubTopicManager()


def add_cli_options(parser: argparse.ArgumentParser):
    """
    Attaches pubsub-specific command-line interface (CLI) arguments to the given
    CLI parser.
    """
    default_client_id = parser.prog[:-3] if parser.prog.endswith('.py') else parser.prog
    pubsub_group = parser.add_argument_group(title='NATS configuration')
    pubsub_group.add_argument('--pubsub-client-id',
                             type=str,
                             default=default_client_id,
                             help=f'Pub/Sub client ID to use for publishers/subcribers.  If not specified, defaults to "{default_client_id}"')

def process_cli_options(args: argparse.Namespace, **kwargs):
    """
    Configures this module according to the provided CLI arguments and keyword
    arguments (see below).

    Specifically, configures the NatsTopicManager singleton.

    kwargs::
        pubsub:
            url: <NATS server URL>
            clients:
                <client-id>:
                    publishes:          # optional
                        - <topic1>
                        - ...
                        - <topicN>
                    consumers:          # optional
                        - <topic1>
                        - ...
                        - <topicN>
    """
    TOPIC_MANAGER.configure(args.pubsub_client_id, kwargs.get('pubsub', {}))

def get_topic_publisher(topic_name: str) -> 'TopicPublisher':
    """
    Returns a TopicPublisher for the given topic_name.  The topic must be configured
    as 'publishes' in the 'pubsub' configuration, else raises NoSuchTopicPublisher.

    All calls to this function with a given name return the same TopicPublisher
    instance. This means that publisher instances never need to be passed between
    different parts of an application.

    Prerequisite: pubsub.process_cli_options
    """
    return TOPIC_MANAGER.get_topic_publisher(topic_name)

def add_topic_callback(topic_name: str, callback: ConsumerCallback):
    """
    Registers the given callback for invocation upon receipt of messages on
    topic_name.  The topic must be configured as 'consumes' in the 'pubsub'
    configuration, else raises NoSuchTopicConsumer.

    Prerequisite: pubsub.process_cli_options
    """
    TOPIC_MANAGER.add_topic_callback(topic_name, callback)

async def connect():
    """
    Connects to the NATS broker and begins processing publish/subscribe
    actions.
    """
    await TOPIC_MANAGER.connect()

async def disconnect():
    """
    Concludes processing of publish/subscribe actions and disconnects from the
    NATS broker.
    """
    await TOPIC_MANAGER.disconnect()
