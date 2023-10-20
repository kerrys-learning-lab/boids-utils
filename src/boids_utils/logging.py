"""
Configures logging.
"""
import argparse
import logging
import logging.config

def add_cli_options(parser: argparse.ArgumentParser):
    """
    Attaches logging-specific command-line interface (CLI) arguments to the given
    CLI parser.
    """
    logging_group = parser.add_argument_group('Logging')
    verbosity_group = logging_group.add_mutually_exclusive_group()
    verbosity_group.add_argument('-v', '--verbose', action='store_true')
    verbosity_group.add_argument('-s', '--silent', action='store_true')
    logging_group.add_argument('--no-color', action='store_true')

def process_cli_options(args: argparse.Namespace, **kwargs):
    """
    Configures this module according to the provided CLI arguments and keyword
    arguments.
    """
    logging_level = logging.DEBUG if args.verbose else logging.ERROR if args.silent else logging.INFO
    logging_config = kwargs.get('logging')

    if logging_config:
        logging_config['loggers'][''] = {
            'handlers': ['stdout' if args.no_color else 'colorized_stdout'],
            'level': logging_level
        }
        logging.config.dictConfig(logging_config)
    else:
        logging.basicConfig(format='%(asctime)s - %(levelname)-6s - %(name)20s - %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            level=logging_level)
