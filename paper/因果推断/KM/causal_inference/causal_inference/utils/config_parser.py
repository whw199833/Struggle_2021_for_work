"""Helper functions for config parsing."""
import os
import argparse
from configparser import ConfigParser
from enum import Enum


class Converters(Enum):
    @staticmethod
    def string_list_converter(s):
        """Converter for a comma-separated list of strings."""
        return [part.strip() for part in s.split(',')]

    @staticmethod
    def bool_converter(s):
        """Converter for a boolean."""
        if s.lower() in ['t', 'true', 'True', '1']:
            return True
        if s.lower() in ['f', 'false', 'False', '0']:
            return False

        raise ValueError('Failed to parse {}'.format(s))


def create_dict_from_ini_file(config_filename,
                              converter_rules,
                              default_values=None):
    """Create a config dict from a config file.

    Args:
        config_filename (): a config file (*.ini).
        converter_rules (): a dict mapping all desired keys to converters.
        Keys not in this dict will not be ignored.
        default_values(): a dict of default values for all optional configs.
        Keys not in the dict are not optional.

    Returns:
        A parsed dict.

    """
    # Initialize the dict.
    config_dict = dict()
    if not default_values:
        default_values = dict()

    # Initialize the config parser.
    if not os.path.exists(config_filename):
        # Provide a more meaningful error here.
        raise ValueError(
            '"{0}" is not a valid file path'.format(config_filename))
    with open(config_filename) as config_file:
        config = ConfigParser()
        config.read_file(config_file)

    # Read from config_parser.
    for key, converter in converter_rules.items():
        value = None
        for section in config.sections():
            if config.has_option(section, key):
                value = config.get(section, key)
        if value:
            config_dict[key] = converter(value)
        elif key in default_values:
            config_dict[key] = default_values[key]
        else:
            raise ValueError('Cannot find {} in {}'.format(
                key, config_filename))

    return config_dict


def create_dict_from_argv(argv, converter_rules, default_values=None):
    """Create a config dict from sys.argv or equivalence.

    Args:
        argv (): sys.argv or equivalence.
        converter_rules (): a dict mapping all desired keys to converters.
        Keys not in this dict will not be ignored.
        default_values(): a dict of default values for all optional configs.
        Keys not in the dict are not optional.

    Returns:
        A parsed dict.

    """
    # Initialize the dict.
    config_dict = dict()
    if not default_values:
        default_values = dict()

    # Initialize the argparse.
    parser = argparse.ArgumentParser('')
    for k, v in converter_rules.items():
        if k in default_values:
            parser.add_argument('--' + k,
                                help='converter: ' + v.__name__,
                                default=None,
                                required=False)
        else:
            parser.add_argument('--' + k,
                                help='converter: ' + v.__name__,
                                required=True)

    args, _ = parser.parse_known_args(argv)

    # Read from argparse.
    for key, converter in converter_rules.items():
        value = args.__getattribute__(key)
        if value:
            config_dict[key] = converter(value)
        else:
            config_dict[key] = default_values[key]

    return config_dict
