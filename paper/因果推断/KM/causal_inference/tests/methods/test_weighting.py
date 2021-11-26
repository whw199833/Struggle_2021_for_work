import unittest
from causal_inference.datasets import load_builtin, Dataset
from causal_inference.estimators.weighting import Weighting


class TestPropensityScoreWeighting(unittest.TestCase):
    dataset = Dataset(load_builtin("lalonde"), [
        "age", "educ", "black", "hispan", "married", "nodegree", "re74", "re75"
    ], "treat", ["re78"])

    def test_glm(self):
        estimator = Weighting(self.dataset)
        results = estimator.do_all(estimand_list=['ATT'],
                                   method="glm",
                                   random_seed=42)['ate_table']
        att_table = results[results.Estimand == 'ATT']
        self.assertAlmostEqual(att_table['Estimate'][0], 1222, delta=100)
        # self.assertAlmostEqual(att_table['Std. Err.'][0], 788, delta=10)
        # self.assertAlmostEqual(att_table['Lower CI (95%)'][0], -321, delta=10)
        # self.assertAlmostEqual(att_table['Upper CI (95%)'][0], 2766, delta=10)

    def test_cbps(self):
        estimator = Weighting(self.dataset)
        results = estimator.do_all(estimand_list=['ATT'],
                                   method="cbps",
                                   random_seed=42)['ate_table']
        att_table = results[results.Estimand == 'ATT']
        self.assertAlmostEqual(att_table['Estimate'][0], 1249, delta=100)
        # self.assertAlmostEqual(att_table['Std. Err.'][0], 788, delta=10)
        # self.assertAlmostEqual(att_table['Lower CI (95%)'][0], -295, delta=10)
        # self.assertAlmostEqual(att_table['Upper CI (95%)'][0], 2793, delta=10)

    def test_ec(self):
        estimator = Weighting(self.dataset)
        results = estimator.do_all(estimand_list=['ATT'],
                                   method="ec",
                                   random_seed=42)['ate_table']
        att_table = results[results.Estimand == 'ATT']
        self.assertAlmostEqual(att_table['Estimate'][0], 1241, delta=100)
        # self.assertAlmostEqual(att_table['Std. Err.'][0], 791, delta=50)
        # self.assertAlmostEqual(att_table['Lower CI (95%)'][0], -309, delta=50)
        # self.assertAlmostEqual(att_table['Upper CI (95%)'][0], 2790, delta=50)

    def test_optweight(self):
        estimator = Weighting(self.dataset)
        results = estimator.do_all(estimand_list=['ATT'],
                                   method="optweight",
                                   random_seed=42)['ate_table']
        att_table = results[results.Estimand == 'ATT']
        self.assertAlmostEqual(att_table['Estimate'][0], 1200, delta=100)
        # self.assertAlmostEqual(att_table['Std. Err.'][0], 787, delta=10)
        # self.assertAlmostEqual(att_table['Lower CI (95%)'][0], -342, delta=10)
        # self.assertAlmostEqual(att_table['Upper CI (95%)'][0], 2742, delta=10)
