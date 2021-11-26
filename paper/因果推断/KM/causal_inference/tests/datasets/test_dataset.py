import os
from unittest import TestCase
from unittest.mock import patch

import numpy as np
import pandas as pd

from causal_inference.datasets import Dataset


class TestDataset(TestCase):
    _lalonde_config = dict({
        'dataset':
        'lalonde',
        'dataset_filter':
        'age>=0',
        'covariates': ['age', 'educ', 'black', 'hispan', 'married', 're75'],
        'treat':
        'treat',
        'outcomes': ['re78'],
        'max_num_users':
        614
    })
    _lalonde_filename = os.path.join(
        os.path.dirname(__file__),
        '../../causal_inference/datasets/data/lalonde.csv')

    def test_from_malformed_data(self):
        np.random.seed(42)
        covariates = ['A', 'B']
        treat_name = 'C'
        outcome_names = ['D', 'E']
        data = pd.DataFrame(np.random.randint(0, 2, size=(100, 5)),
                            columns=covariates + [treat_name] + outcome_names)
        self.assertEqual((100, 5), data.shape)

        # 1. Problematic treat.
        data1 = data.copy()
        data1.loc[0, treat_name] = 2
        self.assertRaises(Exception, Dataset, data1, covariates, treat_name,
                          outcome_names)
        data1[treat_name] = 0
        self.assertRaises(Exception, Dataset, data1, covariates, treat_name,
                          outcome_names)
        data1[treat_name] = 1
        self.assertRaises(Exception, Dataset, data1, covariates, treat_name,
                          outcome_names)

        # 2. Problematic covariates.
        data1 = data.copy()
        data1[covariates[0]] = 'Hello world'
        self.assertRaises(Exception, Dataset, data1, covariates, treat_name,
                          outcome_names)

        # 3. Problematic column name.
        data1 = data.copy()
        data1 = data1.rename(columns={covariates[0]: 'wrong_covariates_name'})
        self.assertRaises(Exception, Dataset, data1, covariates, treat_name,
                          outcome_names)

    def test_from_local_file(self):
        # Test loading builtin dataset.
        dataset = Dataset.from_local_file(self._lalonde_config)
        self.assertEqual(dataset.data.shape[0],
                         self._lalonde_config['max_num_users'])

        # Test loading from file.
        config = self._lalonde_config.copy()
        config['dataset'] = self._lalonde_filename
        dataset = Dataset.from_local_file(config)
        self.assertEqual(dataset.data.shape[0], config['max_num_users'])
        self.assertEqual(dataset.data.shape[1], 8)
        self.assertEqual(len(dataset.covariates), 6)

        config = self._lalonde_config.copy()
        config['categorical_covariates'] = ['educ']
        dataset = Dataset.from_local_file(config)
        self.assertEqual(dataset.data.shape[0], config['max_num_users'])
        self.assertEqual(dataset.data.shape[1], 26)
        self.assertEqual(len(dataset.covariates), 24)

    if os.environ.get('SPARK_HOME'):

        @patch('pytoolkit3.TDWSQLProvider')
        def test_from_tdw_table(self, mock_provider):
            from pyspark.sql import SQLContext
            from pyspark.sql import SparkSession

            # Prepare TDWSQLProvider.table mock.
            spark = SparkSession.builder.appName(
                'Causal Inference').getOrCreate()
            df = SQLContext(spark.sparkContext).createDataFrame(
                pd.read_csv(self._lalonde_filename))
            mock_provider.return_value.table.return_value = df

            # Test loading builtin dataset.
            dataset = Dataset.from_tdw_table(spark, self._lalonde_config)
            self.assertEqual(dataset.data.shape[0],
                             self._lalonde_config['max_num_users'])

            # Test loading from file.
            config = self._lalonde_config.copy()
            config['dataset'] = 'db_name::table_name'
            dataset = Dataset.from_tdw_table(spark, config)
            self.assertEqual(dataset.data.shape[0], config['max_num_users'])
            config['tdw_username'] = 'xx'
            config['tdw_password'] = 'xx'
            dataset = Dataset.from_tdw_table(spark, config)
            self.assertEqual(dataset.data.shape[0], config['max_num_users'])

            # Test malformed dataset config.
            config = self._lalonde_config.copy()
            config['dataset'] = 'table_name'
            self.assertRaises(Exception, Dataset.from_tdw_table, spark, config)
            config['dataset'] = 'table_name;'
            self.assertRaises(Exception, Dataset.from_tdw_table, spark, config)

            # Finish.
            spark.sparkContext.stop()

    def test_one_hot_encoding(self):
        data = pd.DataFrame.from_dict({
            'treat': [0, 0, 1, 1],
            'cat1': ['F', 'M', 'F', 'M'],
            'cat2': [1, 1, 2, 2],
            'norm1': [1, 2, 3, 4],
            'outcome': [0, 0, 0, 0]
        })
        dataset = Dataset(data, ['cat1', 'cat2', 'norm1'],
                          'treat', ['outcome'],
                          categorical_covariates=['cat1', 'cat2'])
        self.assertEqual((4, 7), dataset.data.shape)
        self.assertEqual((4, 5), dataset.get_covariates().shape)
        self.assertEqual(5, len(dataset.covariates))

        self.assertRaises(Exception,
                          Dataset,
                          data, ['cat1', 'norm1'],
                          'treat', ['outcome'],
                          categorical_covariates=['cat1', 'cat2'])
