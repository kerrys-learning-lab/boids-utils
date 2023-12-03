""" Utilities for interacting with OpenAPI generated code. """
import argparse
import logging
import os
import typing
import yaml
import boids_api.boids
import boids_api.boids.base_model

OpenApiModel = boids_api.boids.base_model.Model

LOGGER = logging.getLogger(__name__)


class Spec:
    """ Represents and OpenAPI specification loaded from YAML """

    PATH_MAPPING = {
        boids_api.boids.SessionConfiguration: "#/components/schemas/SessionConfiguration"
    }

    def __init__(self, args: argparse.Namespace) -> None:
        self._path, self._raw = self._load_spec(args)

        self._default_offset = None
        self._default_limit = None

        self._raw = self._resolve(self._raw)

    @property
    def path(self) -> str:
        """ Returns the full path of this OpenAPI spec """
        return self._path

    @property
    def dirname(self) -> str:
        """ Returns the directory name component of this OpenAPI spec """
        return os.path.dirname(self._path)

    @property
    def basename(self) -> str:
        """ Returns the file name component of this OpenAPI spec """
        return os.path.basename(self._path)

    @property
    def title(self):
        """ Returns the title of this OpenAPI spec """
        return self._raw['info']['title']

    @property
    def default_offset(self):
        """ Returns the default value of the 'offset' query parameter """
        if not self._default_offset:
            spec_value = self['#/components/parameters/offset_query/schema/default']
            self._default_offset = spec_value or 0
        return self._default_offset

    @property
    def default_limit(self):
        """ Returns the default value of the 'limit' query parameter """
        if not self._default_limit:
            spec_value = self['#/components/parameters/limit_query/schema/default']
            self._default_limit = spec_value or 20
        return self._default_limit

    def __len__(self):
        return len(self._raw)

    def __getitem__(self, key):
        keys: list = key.split('/')
        if keys.pop(0) != '#':
            raise RuntimeError(
                f'Invalid item path (must start with "#"): {key}')

        value = self._raw
        for k in keys:
            value = value[k]

        return value

    def _resolve(self, value: typing.Any) -> dict:
        if isinstance(value, dict):
            reference = value.get('$ref')
            if reference:
                return self._resolve(self[reference])

            return {k: self._resolve(v) for k, v in value.items()}

        if isinstance(value, list):
            return [self._resolve(v) for v in value]

        return value

    def expand_defaults(self, value: OpenApiModel, clss: type[OpenApiModel]) -> OpenApiModel:
        ''' For the given value, applies defaults from given class specification.

            Properly handles objects and arrays of objects.'''
        # Convert from class/type to reference format (e.g., #/components/schemas/Foo)
        classname_path = Spec.PATH_MAPPING[clss]

        # Retrieve the actual class OpenAPI Specification
        class_specification = self[classname_path]

        # Expand defaults:
        expanded = self._expand_defaults(value.to_dict(), class_specification)

        return clss.from_dict(expanded)

    def _expand_defaults(self, destination: typing.Union[dict, list], source_spec: dict) -> dict:
        if source_spec['type'] == 'object':
            object_properties_spec: dict = source_spec.get('properties', {})
            for attr_name, attr_spec in object_properties_spec.items():
                current_value = destination.get(attr_name, {})
                default_value = self._expand_defaults(current_value, attr_spec)
                if attr_name not in destination and default_value is not None:
                    destination[attr_name] = default_value
            return destination

        if source_spec['type'] == 'array':
            if destination is not None and not isinstance(destination, list):
                raise RuntimeError('Expected type list')

            return [self._expand_defaults(dest, source_spec['items']) for dest in destination]

        return source_spec.get('default')

    def _load_spec(self, args: argparse.Namespace) -> None:
        paths_to_check = []
        if args.openapi_spec_path:
            paths_to_check.append(args.openapi_spec_path)
        else:
            if not args.openapi_skip_default_spec_path:
                paths_to_check.append('/etc/boids-api/openapi.yaml')
            if not args.openapi_skip_module_spec_path:
                path = boids_api.__file__
                path = os.path.dirname(path)
                path = os.path.join(path, 'openapi', 'openapi.yaml')
                paths_to_check.append(path)

        for path in paths_to_check:
            LOGGER.debug(f'Looking for OpenAPI spec at {path}')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as yaml_content:
                    LOGGER.info(f'Using OpenAPI spec at {path}')
                    return (path, yaml.safe_load(yaml_content))

        raise RuntimeError("Unable to locate Boids API YAML")


def to_SessionState(value: str) -> boids_api.boids.SessionState:  # pylint: disable=invalid-name
    """ Converts the given string value to a SessionState enum """
    try:
        return getattr(boids_api.boids.SessionState, value) if value is not None else None
    except AttributeError:
        # pylint: disable-next=raise-missing-from
        raise RuntimeError(
            f'Could not convert "{value}" to boidsapi.boids.SessionState')


def merge_models(dest: OpenApiModel, source: OpenApiModel) -> OpenApiModel:
    """ Non-destructively merges source into destination """
    if type(dest) is type(source):
        raise RuntimeError(
            f"Merging of mismatched types not allowed({type(dest)} vs {type(source)})")
    for field_name in dest.openapi_types:
        if field_name in source:
            updated_value = getattr(source, field_name)
            if isinstance(updated_value, OpenApiModel):
                updated_value = merge_models(
                    getattr(dest, field_name), updated_value)
            setattr(dest, field_name, updated_value)
    return dest


def _merge(destination: dict, source: dict) -> dict:
    result = dict(destination)
    for key, value in source.items():
        if isinstance(value, dict):
            value = _merge(result.get(key, {}), value)
        result[key] = value

    return result


# pylint: disable-next=invalid-name
instance: Spec = None


def add_cli_options(parser: argparse.ArgumentParser):
    """
    Attaches openapi-specific command-line interface (CLI) arguments to the given
    CLI parser.
    """
    openapi_group = parser.add_argument_group(title='OpenAPI configuration')
    openapi_group.add_argument('--openapi-spec-path',
                               default=None,
                               help='Path to OpenAPI specification.  If specified, skips other search paths.')
    openapi_group.add_argument('--openapi-skip-default-spec-path',
                               action='store_true',
                               help='Skips the default OpenAPI spec path (/etc/boids-api/openapi.yaml)')
    openapi_group.add_argument('--openapi-skip-module-spec-path',
                               action='store_true',
                               help='Skips searching for openapi.yaml within the boids_api python module')


def process_cli_options(args: argparse.Namespace, **_):
    """
    Configures this module according to the provided CLI arguments and keyword
    arguments (see below).
    """
    # pylint: disable-next=global-statement,invalid-name
    global instance
    instance = Spec(args)
    return instance
