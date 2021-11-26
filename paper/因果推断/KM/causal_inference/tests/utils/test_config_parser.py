from unittest import TestCase
import tempfile
from causal_inference.utils.config_parser import Converters
from causal_inference.utils.config_parser import create_dict_from_ini_file
from causal_inference.utils.config_parser import create_dict_from_argv


class TestConfigParser(TestCase):

    converter_rules = dict({
        'str':
        str,
        'str_list':
        Converters.string_list_converter,
        'bool':
        Converters.bool_converter,
        'int':
        int,
        'float':
        float,
        'int_optional':
        int,
        'str_list_optional':
        Converters.string_list_converter
    })
    default_values = dict({'int_optional': 1, 'str_list_optional': ['A', 'B']})
    expected_dict = dict({
        'str': 'str',
        'str_list': ['str1', 'str2'],
        'bool': True,
        'int': 42,
        'float': 42.0,
        'int_optional': 1,
        'str_list_optional': ['A', 'B']
    })

    def test_create_dict_from_ini_file(self):
        with tempfile.TemporaryDirectory() as dirname:
            # Test without default values.
            config_filename_full = dirname + 'config_full.ini'
            with open(config_filename_full, 'w') as f:
                f.write("""
                ['Defaults']
                str=str
                str_list=str1,str2
                bool=True
                int=42
                float=42.0
                int_optional=1
                str_list_optional=A,B
                """)
            output_dict = create_dict_from_ini_file(config_filename_full,
                                                    self.converter_rules)
            self.assertEqual(self.expected_dict, output_dict)
            # Test with default values.
            config_filename_partial = dirname + 'config_partial.ini'
            with open(config_filename_partial, 'w') as f:
                f.write("""
                ['Defaults']
                str=str
                str_list=str1,str2
                bool=True
                int=42
                float=42.0
                """)
            self.assertRaises(ValueError, create_dict_from_ini_file,
                              config_filename_partial, self.converter_rules)
            output_dict = create_dict_from_ini_file(config_filename_partial,
                                                    self.converter_rules,
                                                    self.default_values)
            self.assertEqual(self.expected_dict, output_dict)

    def test_create_dict_from_argv(self):
        # Test without default values.
        argv_full = [
            '--str', 'str', '--str_list', 'str1,str2', '--bool', 'True',
            '--int', '42', '--float', '42.0', '--int_optional', '1',
            '--str_list_optional', 'A,B'
        ]
        output_dict = create_dict_from_argv(argv_full, self.converter_rules)
        self.assertEqual(self.expected_dict, output_dict)
        # Test with default values.
        argv_partial = [
            '--str', 'str', '--str_list', 'str1,str2', '--bool', 'True',
            '--int', '42', '--float', '42.0'
        ]
        self.assertRaises(SystemExit, create_dict_from_argv, argv_partial,
                          self.converter_rules)
        output_dict = create_dict_from_argv(argv_partial, self.converter_rules,
                                            self.default_values)
        self.assertEqual(self.expected_dict, output_dict)
