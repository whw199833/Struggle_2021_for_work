import importlib.machinery
import importlib.util
import os
import sys
import unittest
import unittest.mock
from tempfile import TemporaryDirectory


class TestDoCausalInference(unittest.TestCase):
    config_file_content = """
    [Basic]
    dataset=lalonde
    dataset_filter=age>=0
    covariates=age,educ,black,hispan,married,re75
    treat=treat
    outcomes=re78
"""
    config_argv = [
        '--dataset', 'lalonde', '--dataset_filter=age>=0', '--covariates',
        'age,educ,black,hispan,married,re75', '--treat', 'treat', '--outcomes',
        're78'
    ]

    @classmethod
    def setUpClass(cls):
        filename = os.path.join(os.path.dirname(__file__),
                                '../do_causal_inference.py')
        loader = importlib.machinery.SourceFileLoader('', filename)
        spec = importlib.util.spec_from_loader(loader.name, loader)
        cls.do = importlib.util.module_from_spec(spec)
        loader.exec_module(cls.do)

    @unittest.mock.patch('causal_inference.CausalEstimatorWrapper.inference')
    def test_main_local_mode(self, mock_inference):
        # Mock the inference method.
        mock_inference.return_value = ('ok', '')

        # Correct arguments.
        temp_dir = TemporaryDirectory()
        log_filename = os.path.join(temp_dir.name, 'log.csv')
        test_args = ['xx.py', 'local', 'argv'] + self.config_argv + [
            '--output_filename', log_filename
        ]
        with unittest.mock.patch.object(sys, 'argv', test_args):
            self.do.main()
        with open(log_filename, 'r') as f_log:
            self.assertEqual('ok', f_log.read())
        temp_dir.cleanup()

        temp_dir = TemporaryDirectory()
        config_filename = os.path.join(temp_dir.name, 'config.ini')
        with open(config_filename, 'w') as f:
            f.write(self.config_file_content)
        test_args = [
            'xx.py', 'local', 'file', '--config_filename', config_filename
        ]
        with unittest.mock.patch.object(sys, 'argv', test_args):
            results = self.do.main()
        self.assertEqual('ok', results)
        temp_dir.cleanup()

        # Malformed arguments.
        test_args = ['xx.py', 'local', 'argv']
        with unittest.mock.patch.object(sys, 'argv', test_args):
            self.assertRaises(SystemExit, self.do.main)

        test_args = ['xx.py', 'local', 'file']
        with unittest.mock.patch.object(sys, 'argv', test_args):
            self.assertRaises(ValueError, self.do.main)

    if os.environ.get('SPARK_HOME'):

        @unittest.mock.patch(
            'causal_inference.CausalEstimatorWrapper.inference')
        def test_main_tdw_mode(self, mock_inference):
            # Mock the inference method.
            mock_inference.return_value = ('ok', '')

            # Correct arguments.
            test_args = ['xx.py', 'yard', 'argv'] + self.config_argv + [
                '--tdw_username', 'username', '--tdw_password', 'password'
            ]
            with unittest.mock.patch.object(sys, 'argv', test_args):
                results = self.do.main()
            self.assertEqual('ok', results)

            test_args = ['xx.py', 'tesla', 'argv'] + self.config_argv
            with unittest.mock.patch.object(sys, 'argv', test_args):
                results = self.do.main()
            self.assertEqual('ok', results)

            # Malformed arguments.
            test_args = ['xx.py', 'yard', 'argv']
            with unittest.mock.patch.object(sys, 'argv', test_args):
                self.assertRaises(SystemExit, self.do.main)

            test_args = ['xx.py', 'yard', 'file']
            with unittest.mock.patch.object(sys, 'argv', test_args):
                self.assertRaises(ValueError, self.do.main)
