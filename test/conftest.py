import argparse
import logging
import pytest
import boids_utils.config
import boids_utils.elastic
import boids_utils.logging
import boids_utils.openapi
import boids_utils.pubsub
import test.testcontainers.nats
import test.testcontainers.elasticsearch
import time

LOGGER = logging.getLogger('conftest')
TEST_CLIENT_ID = 'gateway'
TEST_TOPIC = 'boids.test.topic'
NATS_IMAGE="nats:2.9.23"
ELASTICSEARCH_IMAGE="bitnami/elasticsearch:8.9.1-debian-11-r2"

@pytest.fixture(scope='session', autouse=True)
def args():
    _args = argparse.Namespace(verbose=True,
                               no_color=False,
                               openapi_spec_path='/etc/boids-api/openapi.yaml',
                               pubsub_client_id=TEST_CLIENT_ID,
                               elastic_skip_init=False,
                               config=[
                                   'conf.d/logging.yaml',
                                   'conf.d/elasticsearch.yaml',
                                   'conf.d/pubsub.yaml'
                               ])

    boids_utils.config.process_cli_options(_args)
    boids_utils.logging.process_cli_options(_args, **boids_utils.config.instance)

    return _args


@pytest.fixture(scope="session")
def broker(args: argparse.Namespace):
    container = test.testcontainers.nats.NATSContainer(NATS_IMAGE)

    LOGGER.info(f'Starting pub/sub broker test container ({NATS_IMAGE})...')
    container.start()

    yield container

    container.stop()

@pytest.fixture(scope="session")
def elasticsearch(args: argparse.Namespace):
    container = test.testcontainers.elasticsearch.ElasticSearchContainer(ELASTICSEARCH_IMAGE)
    container.with_env("xpack.security.enabled", "false")

    LOGGER.info(f'Starting Elasticsearch test container ({ELASTICSEARCH_IMAGE})...')

    container.start()

    yield container

    container.stop()



@pytest.fixture(scope='session')
def test_config(args: argparse.Namespace,
                broker: test.testcontainers.nats.NATSContainer,
                elasticsearch: test.testcontainers.elasticsearch.ElasticSearchContainer):
    boids_utils.config.instance['elasticsearch']['server'] = elasticsearch.get_url()
    boids_utils.config.instance['pubsub']['url'] = broker.get_server_url()
    boids_utils.config.instance['pubsub']['clients'][TEST_CLIENT_ID]['publishes'].append(TEST_TOPIC)
    boids_utils.config.instance['pubsub']['clients'][TEST_CLIENT_ID]['consumes'] = [
        TEST_TOPIC,
        'boids.sessions'
    ]

    boids_utils.elastic.process_cli_options(args, **boids_utils.config.instance)
    boids_utils.openapi.process_cli_options(args, **boids_utils.config.instance)
    boids_utils.pubsub.process_cli_options(args, **boids_utils.config.instance)

    yield boids_utils.config.instance
