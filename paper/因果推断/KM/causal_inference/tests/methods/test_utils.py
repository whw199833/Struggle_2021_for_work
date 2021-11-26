from unittest import TestCase
import numpy as np

from causal_inference.estimators.utils import is_binary
from causal_inference.estimators.utils import get_mean_se_confint


class TestUtils(TestCase):
    def test_is_binary(self):
        self.assertEqual(True, is_binary([0]))
        self.assertEqual(True, is_binary([1]))
        self.assertEqual(True, is_binary([0, 1]))
        self.assertEqual(False, is_binary([2]))
        self.assertEqual(True, is_binary(np.array([])))

    def test_get_mean_se_confint(self):
        np.random.seed(42)
        arr = np.random.normal(1.0, 0.001, 10000)
        m, se, _, _ = get_mean_se_confint(arr, confidence=0.95)
        self.assertAlmostEqual(1.0, m, places=2)
        self.assertAlmostEqual(0.001, se, places=2)
