""" Provides file-based configuration via YAML """
import argparse
import typing
import mergedeep
import yaml

# pylint: disable-next=invalid-name
instance = {}

def add_cli_options(parser: argparse.ArgumentParser):
    """
    Attaches config-specific command-line interface (CLI) arguments to the given
    CLI parser.
    """
    config_group = parser.add_argument_group(title='Additional configuration')
    config_group.add_argument('config',
                              nargs='+',
                              help='Specify a YAML configuration file')

def process_cli_options(args: argparse.Namespace, **_):
    """
    Configures this module according to the provided CLI arguments and keyword
    arguments.
    """
    # pylint: disable-next=global-statement,invalid-name
    global instance
    instance = vars(args)
    for file in args.config:
        with open(file, 'r', encoding='utf-8') as fstream:
            instance = mergedeep.merge(instance, yaml.safe_load(fstream))
    return instance

def get(key: str, default: typing.Any = None) -> typing.Any:
    """ Returns the configuration value for the given key, or 'default' if
        key does not exist in the configuration. """
    if not instance:
        raise RuntimeError('Configuration not initialized')
    return instance.get(key, default)
