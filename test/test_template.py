import logging
import os.path
import uuid
import pytest
import boids_utils
import boids_utils.template

LOGGER = logging.getLogger(__name__)

@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_render():
    expected_uuid = boids_utils.mk_uuid()
    template_output_context = boids_utils.template.render('test/test-template.yaml.j2',
                                                          uuid=expected_uuid,
                                                          labels={'foo': 'bar', 'baz': 'bop'},
                                                          image_spec='foo:bar')

    assert os.path.exists(template_output_context.path)

    with template_output_context as file:
        file_contents = file.read()

        assert f'engine-{expected_uuid}' in file_contents

    assert os.path.exists(template_output_context.path) == False
