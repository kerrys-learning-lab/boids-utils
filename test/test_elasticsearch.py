import logging
import math
import pytest
import time
import boidsapi.model
import boids_utils
import boids_utils.elastic
import boids_utils.config

LOGGER = logging.getLogger(__name__)

def create_test_session_config(count=1, title='Test title', num_boids=10):
    results = []
    for i in range(count):
        value = boidsapi.model.SessionConfigurationStatus(title=f'{title} {i}',
                                                          num_boids=num_boids,
                                                          state= boidsapi.model.SessionState.PENDING,
                                                          uuid=boids_utils.mk_uuid(),
                                                          created=boids_utils.nowutc(stringify=True),
                                                          modified=boids_utils.nowutc(stringify=True))
        results.append(value)
    return results if count > 1 else results[0]

@pytest.mark.asyncio
async def test_index_save_new(test_config):
    expected = create_test_session_config()
    boids_utils.elastic.indices.session_configuration.save(expected)
    actual = boids_utils.elastic.indices.session_configuration.get(expected.uuid)

    assert actual.uuid  == expected.uuid
    assert actual.title == expected.title
    assert actual.state == expected.state

@pytest.mark.asyncio
async def test_index_save_existing(test_config):
    expected = create_test_session_config()
    boids_utils.elastic.indices.session_configuration.save(expected)

    expected.state = boidsapi.model.SessionState.RUNNING
    expected.modified = boids_utils.nowutc(stringify=True)

    boids_utils.elastic.indices.session_configuration.save(expected)
    actual = boids_utils.elastic.indices.session_configuration.get(expected.uuid)

    assert actual.uuid  == expected.uuid
    assert actual.title == expected.title
    assert actual.state == expected.state

@pytest.mark.asyncio
async def test_index_search_default_pagination(test_config):
    UNIQUE_TITLE='test_index_search_default_pagination'
    UNIQUE_NUM_BOIDS=42
    expected_list = create_test_session_config(10, UNIQUE_TITLE, num_boids=UNIQUE_NUM_BOIDS)

    for expected in expected_list:
        boids_utils.elastic.indices.session_configuration.save(expected)

    results, pagination = boids_utils.elastic.indices.session_configuration.search(title=UNIQUE_TITLE,
                                                                                   num_boids=UNIQUE_NUM_BOIDS)

    assert len(results)      == len(expected_list)
    assert pagination.offset == 0
    assert pagination.limit  == 20
    assert pagination.total  == len(expected_list)

@pytest.mark.asyncio
async def test_index_search_odd_pagination(test_config):
    UNIQUE_TITLE='test_index_search_odd_pagination'
    UNIQUE_NUM_BOIDS=99
    EXPECTED_NUM_PAGE=4 # 10/3 => 4 pages
    expected_list = create_test_session_config(10, UNIQUE_TITLE, num_boids=UNIQUE_NUM_BOIDS)
    expected_uuids = []

    for expected in expected_list:
        boids_utils.elastic.indices.session_configuration.save(expected)
        expected_uuids.append(expected.uuid)

    original_pagination = boidsapi.model.Pagination(offset=0, limit=3)

    for i in range(EXPECTED_NUM_PAGE):
        original_pagination.offset = i * original_pagination.limit
        results, pagination = boids_utils.elastic.indices.session_configuration.search(title=UNIQUE_TITLE,
                                                                                       num_boids=UNIQUE_NUM_BOIDS,
                                                                                       pagination=original_pagination)

        assert len(results) <= pagination.limit
        assert pagination.total == 10
        assert pagination.offset == i * original_pagination.limit

        for actual in results:
            # Throws ValueError if uuid not present, thus ensuring that each
            # result is expected
            expected_uuids.remove(actual.uuid)

    # Now that all search results should have been returned, we should have
    # matched each uuid, leaving us an empty list of expectations
    assert len(expected_uuids) == 0

@pytest.mark.asyncio
async def test_index_search_index_error_pagination(test_config):
    UNIQUE_TITLE='test_index_search_odd_pagination'
    UNIQUE_NUM_BOIDS=72
    expected_list = create_test_session_config(10, UNIQUE_TITLE, num_boids=UNIQUE_NUM_BOIDS)

    for expected in expected_list:
        boids_utils.elastic.indices.session_configuration.save(expected)

    pagination = boidsapi.model.Pagination(offset=1000, limit=5)

    with pytest.raises(IndexError):
        boids_utils.elastic.indices.session_configuration.search(title=UNIQUE_TITLE,
                                                                 num_boids=UNIQUE_NUM_BOIDS,
                                                                 pagination=pagination)
