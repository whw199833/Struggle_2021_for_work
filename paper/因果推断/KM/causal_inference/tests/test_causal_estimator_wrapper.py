import os
from unittest import TestCase

import pandas as pd

from causal_inference import CausalEstimatorWrapper
from causal_inference.datasets import Dataset
from causal_inference.datasets import generate_datasets

TEST_CONFIG_DIR = os.path.join(os.path.dirname(__file__), './test_configs/')
TEMPLATE_CONFIG_DIR = os.path.join(os.path.dirname(__file__), '../configs/')


class TestCausalEstimatorWrapper(TestCase):
    def _compare_ate(self, results, oracle, relative_error=0.2):
        for result in results:
            if 'ate_table' not in result:
                continue
            ate_table = pd.merge(result['ate_table'],
                                 oracle,
                                 on=['Estimand', 'Outcome'],
                                 how='left',
                                 sort=True)
            for _, row in ate_table.iterrows():
                self.assertAlmostEqual(row['Oracle'],
                                       row['Estimate'],
                                       delta=relative_error * row['Oracle'])

    def test_inference_wrong_config(self):
        # Malformed config file.
        config = dict()
        self.assertRaises(ValueError, CausalEstimatorWrapper, config)

    def test_inference_correct_config(self):
        data, covariates, treat_name, outcome_names, oracle = \
            generate_datasets(100, 1, 'independence', 'dense', 'linear',
                              ['dense'], ['linear'])
        dataset = Dataset(data, covariates, treat_name, outcome_names)

        # Test the local mode.
        config = CausalEstimatorWrapper.default_config
        ci = CausalEstimatorWrapper(config)
        _, results = ci.inference(dataset)
        self._compare_ate(results, oracle)

        # Test the spark mode.
        if os.environ.get('SPARK_HOME'):
            from pyspark.sql import SparkSession

            spark = SparkSession.builder.appName(
                'Causal Inference').getOrCreate()
            sc = spark.sparkContext
            ci = CausalEstimatorWrapper(config)
            results, _ = ci.inference(dataset, spark_context=sc)
            self._compare_ate(results, oracle)
