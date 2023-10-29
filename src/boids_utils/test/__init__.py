''' Provides pytest utilities common to Boids applications '''
import argparse
import asyncio
import logging
import pytest
import testcontainers.core.container
import boids_utils.config
import boids_utils.elastic
import boids_utils.openapi
import boids_utils.pubsub
import boids_utils.logging
import boids_utils.test.containers.nats
import boids_utils.test.containers.elasticsearch

# Disable redefined-outer-name for the entire file because that's how pytest
# fixtures work! Similarly, some test fixtures are dependencies of others,
# even if they don't seem to be used in creation of the fixture (e.g.,
# elasticsarch has a dependency on test_openapi_spec)
#
# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument

TEST_CLIENT_ID: str = 'test'
PRE_TEST_CLI_ARGS=None
POST_TEST_CLI_ARGS=None
PRE_TEST_PUBSUB_BROKER=None
POST_TEST_PUBSUB_BROKER=None
PRE_TEST_ELASTICSEARCH=None
POST_TEST_ELASTICSEARCH=None
PRE_TEST_API_SPEC=None
POST_TEST_API_SPEC=None

LOGGER = logging.getLogger(__name__)
NATS_IMAGE="nats:2.9.23"
ELASTICSEARCH_IMAGE="bitnami/elasticsearch:8.9.1-debian-11-r2"

args: argparse.Namespace = None
docker_containers: list[testcontainers.core.container.DockerContainer] = []

@pytest.fixture(scope="session")
def event_loop():
    ''' Creates and returns a session-scoped asyncio event loop '''
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope='session')
def test_cli_args():
    ''' Creates and returns CLI arguments suitable for testing application
        initialization '''
    global args # pylint: disable=global-statement
    args = argparse.Namespace(verbose=True,
                              no_color=False,
                              openapi_spec_path='/etc/boids-api/openapi.yaml',
                              pubsub_client_id=TEST_CLIENT_ID,
                              elastic_skip_init=False,
                              config=[
                                  '/etc/boids/logging.yaml',
                                  '/etc/boids/elasticsearch.yaml',
                                  '/etc/boids/pubsub.yaml'
                              ])

    if callable(PRE_TEST_CLI_ARGS):
        PRE_TEST_CLI_ARGS() # pylint: disable=not-callable

    boids_utils.config.process_cli_options(args)
    boids_utils.logging.process_cli_options(args, **boids_utils.config.instance)

    if callable(POST_TEST_CLI_ARGS):
        POST_TEST_CLI_ARGS() # pylint: disable=not-callable

    return args

@pytest.fixture(scope='session')
def test_pubsub_broker(test_cli_args: argparse.Namespace,
                       event_loop: asyncio.AbstractEventLoop):
    ''' Creates and returns a NATS testcontainer suitable for use in unit tests '''
    LOGGER.info(f'Starting pub/sub broker test container ({NATS_IMAGE})...')
    container = boids_utils.test.containers.nats.NATSContainer(NATS_IMAGE)

    container.start()

    if callable(PRE_TEST_PUBSUB_BROKER):
        PRE_TEST_PUBSUB_BROKER() # pylint: disable=not-callable

    boids_utils.config.instance['pubsub']['url'] = container.get_server_url()
    boids_utils.pubsub.process_cli_options(test_cli_args,
                                           **boids_utils.config.instance)
    docker_containers.append(container)

    if callable(POST_TEST_PUBSUB_BROKER):
        POST_TEST_PUBSUB_BROKER() # pylint: disable=not-callable

    event_loop.run_until_complete(boids_utils.pubsub.connect())

    yield boids_utils.pubsub

    event_loop.run_until_complete(boids_utils.pubsub.disconnect())

    container.stop()

@pytest.fixture(scope='session')
def test_elasticsearch(test_cli_args: argparse.Namespace,
                       test_openapi_spec: boids_utils.openapi):
    ''' Creates and returns an Elasticsearch testcontainer suitable for use in unit tests '''
    container = boids_utils.test.containers.elasticsearch.ElasticSearchContainer(ELASTICSEARCH_IMAGE)
    container.with_env("xpack.security.enabled", "false")

    LOGGER.info(f'Starting Elasticsearch test container ({ELASTICSEARCH_IMAGE})...')

    container.start()

    if callable(PRE_TEST_ELASTICSEARCH):
        PRE_TEST_ELASTICSEARCH() # pylint: disable=not-callable

    boids_utils.config.instance['elasticsearch']['server'] = container.get_url()
    boids_utils.elastic.process_cli_options(test_cli_args,
                                            **boids_utils.config.instance)
    docker_containers.append(container)

    if callable(POST_TEST_ELASTICSEARCH):
        POST_TEST_ELASTICSEARCH() # pylint: disable=not-callable

    yield boids_utils.elastic

    container.stop()

@pytest.fixture(scope='session')
def test_openapi_spec(test_cli_args: argparse.Namespace):
    ''' Creates and returns an OpenAPI spec suitable for use in unit tests '''
    if callable(PRE_TEST_API_SPEC):
        PRE_TEST_API_SPEC() # pylint: disable=not-callable

    boids_utils.openapi.process_cli_options(test_cli_args,
                                            **boids_utils.config.instance)

    if callable(POST_TEST_API_SPEC):
        POST_TEST_API_SPEC() # pylint: disable=not-callable

    return boids_utils.openapi
