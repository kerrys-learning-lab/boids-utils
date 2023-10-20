import json
import logging
import pytest
import boids_utils.openapi

LOGGER = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_init(test_config):
    uut = boids_utils.openapi.Spec('/etc/boids-api/openapi.yaml')

    session_config = uut._raw['components']['schemas']['SessionConfiguration']
    session_config_str = json.dumps(session_config)
    assert '$ref' not in session_config_str
    assert 'width' in session_config['properties']['world']['properties']

@pytest.mark.asyncio
async def test_getitem(test_config):
    uut = boids_utils.openapi.Spec('/etc/boids-api/openapi.yaml')

    session_config = uut['#/components/schemas/SessionConfiguration']
    assert 'properties' in session_config
    assert 'title' in session_config['properties']
    assert 'state' in session_config['properties']

@pytest.mark.asyncio
async def test_getitem_invalid_root(test_config):
    uut = boids_utils.openapi.Spec('/etc/boids-api/openapi.yaml')

    with pytest.raises(RuntimeError):
      uut['components/foo']

    with pytest.raises(RuntimeError):
      uut['/components/foo']

@pytest.mark.asyncio
async def test_expand_defaults(test_config):
    uut = boids_utils.openapi.Spec('/etc/boids-api/openapi.yaml')

    actual = uut._expand_defaults({}, uut['#/components/schemas/BehaviorConfiguration'])
    assert actual['avoid_walls'] == True
    assert actual['speed_limits']['min'] == 1
    assert actual['speed_limits']['max'] == 100

@pytest.mark.asyncio
async def test_expand_defaults_partial(test_config):
    uut = boids_utils.openapi.Spec('/etc/boids-api/openapi.yaml')

    actual = uut._expand_defaults({'avoid_walls': False, 'speed_limits': {'min': 2}}, uut['#/components/schemas/BehaviorConfiguration'])
    assert actual['avoid_walls'] == False
    assert actual['speed_limits']['min'] == 2
    assert actual['speed_limits']['max'] == 100
