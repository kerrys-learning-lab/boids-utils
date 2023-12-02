""" Utility for CRUD operations on Elastic documents. """
import argparse
import logging
import backoff
import elasticsearch
import elastic_transport
import boids_api.boids
import boids_utils.openapi
import boids_utils.config
from .exceptions import *
from .index import Index
from .manager import Manager


def add_cli_options(parser: argparse.ArgumentParser):
    """
    Attaches elastic-specific command-line interface (CLI) arguments to the given
    CLI parser.
    """
    group = parser.add_argument_group(title='Elasticsearch options')
    group.add_argument('--elastic-skip-init',
                       action='store_true',
                       help='Skip idempotent creation of indices/search-templates')


def process_cli_options(args: argparse.Namespace, **kwargs):
    """
    Configures this module according to the provided CLI arguments and keyword
    arguments.
    """
    elastic_config = kwargs.get('elasticsearch')
    elastic_url = elastic_config["server"]
    connect_backoff()

    if not args.elastic_skip_init:
        Manager.create_indices(elastic_url, **elastic_config)
        Manager.create_search_templates(elastic_url, **elastic_config)


LOGGER = logging.getLogger(__name__)


class Indices:
    """ Collection of *named* Index objects """

    def __init__(self) -> None:
        self.connection = None
        self._session_configuration = Index('boids.sessions',
                                            boids_api.boids.SessionConfigurationStatus)

    def on_connected(self, client: elasticsearch.Elasticsearch):
        """ Called by the elastic module upon successful connection to
            Elasticsearch """
        self.connection = client
        for index in [self._session_configuration]:
            index.on_connected(client)

    @property
    def session_configuration(self) -> Index:
        """ The Index object associated with the session_configuration index """
        self._assert_connected()
        return self._session_configuration

    def _assert_connected(self):
        if not self.connection:
            raise ConnectionError('Not connected')


connection = None       # pylint: disable=invalid-name
indices = Indices()     # pylint: disable=invalid-name


def connect() -> elasticsearch.Elasticsearch:
    """ Connects to Elasticsearch.

        Raises ConfigurationError if required configuration properties are missing.
        Raises ConnectionError if unable to connect to Elasticsearch. """
    global connection   # pylint: disable=invalid-name,global-statement
    try:
        elastic_config = boids_utils.config.get('elasticsearch')
        server = elastic_config["server"]

        LOGGER.debug(f"Connecting to {server}...")
        connection = elasticsearch.Elasticsearch(server)

        info = connection.info()
        LOGGER.info(f"Connected to {server} (v{info['version']['number']})")

        indices.on_connected(connection)

        return connection
    except KeyError as ex:
        # pylint: disable-next=raise-missing-from
        raise ConfigurationError(str(ex))
    except elastic_transport.TransportError as ex:
        raise ConnectionError(str(ex))  # pylint: disable=raise-missing-from


@backoff.on_exception(backoff.constant, ConnectionError, interval=60, logger='elasticsrch')
def connect_backoff():
    """ Repeatedly attempts to connect to Elasticsearch utlizing a constant
        backoff approach. """
    return connect()
