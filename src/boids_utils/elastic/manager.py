""" Manages configured Elasticsearch configuration. """
import logging
import requests

DEFAULT_TIMEOUT_SECONDS=10
GET_INDEX_MAPPING='{elastic_url}/{index_name}/_mapping'
PUT_INDEX_MAPPING='{elastic_url}/{index_name}'
GET_ALL_SEARCH_TEMPLATES='{elastic_url}/_cluster/state/metadata?pretty&filter_path=**.stored_scripts'
PUT_SEARCH_TEMPLATE='{elastic_url}/_scripts/{template_name}'

LOGGER = logging.getLogger(__name__)

class Manager:
    """ Manages configured Elasticsearch configuration. """

    @staticmethod
    def create_indices(elastic_url: str, **config):
        """ Idempotently creates Index mappings according to the provided
            configuration """

        for index, index_spec in config.get('indexes').items():
            index_mappings = index_spec.get('mappings')

            if index_mappings:
                try:
                    LOGGER.debug(f'Checking index {index}')
                    requests.get(GET_INDEX_MAPPING.format(elastic_url=elastic_url,
                                                          index_name=index),
                                 timeout=DEFAULT_TIMEOUT_SECONDS).raise_for_status()
                except requests.exceptions.HTTPError:
                    index_mappings = {'mappings': index_mappings}
                    requests.put(PUT_INDEX_MAPPING.format(elastic_url=elastic_url,
                                                          index_name=index),
                                 json=index_mappings,
                                 timeout=DEFAULT_TIMEOUT_SECONDS).raise_for_status()
                    LOGGER.info(f'Created index {index}')

    @staticmethod
    def create_search_templates(elastic_url: str, **config):
        """ Idempotently creates search templates according to the provided
            configuration """
        response = requests.get(GET_ALL_SEARCH_TEMPLATES.format(elastic_url=elastic_url),
                                timeout=DEFAULT_TIMEOUT_SECONDS)
        response.raise_for_status()
        existing_search_templates = response.json().get('metadata', {}).get('stored_scripts', {})

        for search_template_name, search_template_spec in config.get('search-templates', {}).items():
            LOGGER.debug(f'Checking search-template {search_template_name}')

            if search_template_name not in existing_search_templates:
                requests.put(PUT_SEARCH_TEMPLATE.format(elastic_url=elastic_url,
                                                        template_name=search_template_name),
                             json=search_template_spec,
                             timeout=DEFAULT_TIMEOUT_SECONDS)
                LOGGER.info(f'Created search-template {search_template_name}')
