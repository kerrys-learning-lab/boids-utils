"""
Provides utilities for working with Jinja2 templates.
"""
import logging
import os
import tempfile
import jinja2

LOGGER = logging.getLogger(__name__)

class TemplateContext:
    """ Provides a with-context for a returned temporary template path, removing
        the path upon exiting the with-context. """

    def __init__(self, temp_template_path) -> None:
        self.path = temp_template_path
        self._fstream = None

    def __enter__(self):
        self._fstream = open(self.path, 'r', encoding='utf-8')
        return self._fstream

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.remove()

    def remove(self):
        """ Removes the temporary template file """
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass

env: jinja2.Environment = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"),
                                             autoescape=jinja2.select_autoescape(),
                                             trim_blocks=True,
                                             lstrip_blocks=True)


def render(path, write_to_file=True, **kwargs):
    """ Renders the template and returns (depending on write_to_file) the
        rendered contents or a TemplateContext pointing to a tempfile of
        the rendered contents """
    template = env.get_template(path)
    tmpfile = tempfile.NamedTemporaryFile(mode='w',
                                          encoding='utf-8',
                                          delete=False,
                                          suffix='.yaml')
    content = template.render(**kwargs)

    if write_to_file:
        with tmpfile as writeable:
            writeable.write(content)
            return TemplateContext(tmpfile.name)
    else:
        return content
