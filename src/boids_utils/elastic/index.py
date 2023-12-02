""" Provides CRUD operations on an Elasticsearch index.

    NOTE: There is a built-in assumption/design-decision that all OpenAPI models
          must have a uuid field.

"""
import logging
import typing
import elasticsearch
import boids_api.boids
import boids_utils.openapi
from .exceptions import *   # pylint: disable=wildcard-import,unused-wildcard-import

T = typing.TypeVar('T')


LOGGER = logging.getLogger(__name__)


class Index:
    """ Provides CRUD operations on an Elasticsearch index. """
    ORDER_BY_MAPPING = {
        'title': 'title.keyword'
    }

    REQUIRED_FIELDS = [
        'uuid',
        'created',
        'modified',
    ]

    def __init__(self,
                 index_name: str,
                 cls: type[boids_utils.openapi.OpenApiModel],
                 client: elasticsearch.Elasticsearch = None) -> None:
        self.name = index_name
        self._client = client
        self._type = cls

        Index._assert_required_fields(cls)

    def on_connected(self, client: elasticsearch.Elasticsearch):
        """ Called upon successful connection to Elasticsearch. """
        self._client = client

    def save(self, data: boids_utils.openapi.OpenApiModel):
        """ Saves (indexes) the given object as a document in Elasticsearch. """
        document: dict = data.to_dict()
        LOGGER.debug(
            f'Saving document {data.__class__.__name__} {data.uuid} to {self.name}')
        self._client.index(index=self.name, document=document,
                           id=data.uuid, refresh=True)

    def get(self, uuid) -> boids_utils.openapi.OpenApiModel:
        """
        Returns exactly one OpenAPI model object from the Elasticsearch results
        returned using the given query.
        """
        results = self._client.search(index=self.name,
                                      sort=Index.create_sort_critera(
                                          order_by='-modified'),
                                      size=1,
                                      query=Index.create_search_criteria(uuid=uuid))

        hits: dict = results.get('hits', {})
        data = hits.get('hits', [])

        if len(data) == 0:
            raise DocumentNotFoundError(
                f'{self.name}: No matching documents found')
        if len(data) > 1:
            raise MultipleDocumentsFoundError(
                f'{self.name}: Found {len(data)} documents (expected 1)')

        return self._type.from_dict(data[0]['_source'])

    # pylint: disable=line-too-long
    def search(self,
               pagination: boids_api.boids.Pagination = None,
               **kwargs) -> typing.Tuple[list[boids_utils.openapi.OpenApiModel], boids_api.boids.Pagination]:
        """
        Returns OpenAPI model objects from the Elasticsearch documents in the
        given search results.
        """
        pagination = pagination or boids_api.boids.Pagination(offset=boids_utils.openapi.instance.default_offset,
                                                              limit=boids_utils.openapi.instance.default_limit)
        query = Index.create_search_criteria(**kwargs)
        results: dict = self._client.search(index=self.name,
                                            from_=pagination.offset,
                                            size=pagination.limit,
                                            sort=Index.create_sort_critera(
                                                pagination.order_by),
                                            query=query)
        hits: dict = results.get('hits', {})
        data = hits.get('hits', [])
        hits_total = hits.get('total', {}).get('value', 0)
        LOGGER.debug(
            f'{self.name}: Returning {len(data)} out of {hits_total} hits')

        data = [self._type.from_dict(v['_source']) for v in data]

        pagination.total = hits_total

        if pagination.offset > pagination.total:
            raise IndexError(
                f'Requested pagination offset ({pagination.offset}) greater than total ({pagination.total})')

        return data, pagination

    @staticmethod
    def create_search_criteria(**criteria):
        """
        Returns an Elastic search query-fragment based on the provided criteria.
        """
        must = []
        for key, value in criteria.items():
            if value:
                must.append({'match': {key: value}})

        if must:
            return {'bool': {'must': must}}

        return {'match_all': {}}

    @staticmethod
    def create_sort_critera(order_by: str = None):
        """
        Returns an Elastic sort query-fragment based on the provided 'order_by'
        criteria. The sort query-fragment will be ascending unless the given
        'order_by' criteria begins with a negative sign ('-').

        For example, 'order_by: title' will sort by the title field, ascending;
        whereas 'order_by: -title' will sort by the title field, descending.
        """
        if not order_by:
            return None

        order = "desc" if order_by.startswith('-') else "asc"
        order_by = order_by.strip('-')
        order_by = Index.ORDER_BY_MAPPING.get(order_by, order_by)
        return [{order_by: order}]

    @staticmethod
    def _assert_required_fields(instance_type: type[boids_utils.openapi.OpenApiModel]):
        dummy = instance_type()
        for field in Index.REQUIRED_FIELDS:
            if field not in dummy.attribute_map:
                raise ConfigurationError(
                    f'Expected model {dummy.__class__.__name__} to have a "{field}" field')
