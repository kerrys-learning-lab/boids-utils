import logging
import pytest
import boids_utils.config
import boids_utils.elastic
import boids_utils.logging
import boids_utils.openapi
import boids_utils.pubsub
import boids_utils.test

LOGGER = logging.getLogger('conftest')
TEST_CLIENT_ID = 'boids-utils-test'
TEST_TOPIC = 'boids.test.topic'

def pre_test_pubsub_broker():
    boids_utils.config.instance['pubsub']['clients'][TEST_CLIENT_ID] = {
        'publishes': [TEST_TOPIC],
        'consumes': [TEST_TOPIC],
    }

boids_utils.test.TEST_CLIENT_ID = TEST_CLIENT_ID
boids_utils.test.PRE_TEST_PUBSUB_BROKER = pre_test_pubsub_broker

from boids_utils.test import (event_loop,
                              test_cli_args,
                              test_pubsub_broker,
                              test_elasticsearch,
                              test_openapi_spec)
