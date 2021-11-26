from unittest import TestCase

from causal_inference.datasets.toy_data_loader import load_lalonde


class TestBase(TestCase):
    def test_load_lalonde(self):
        res = load_lalonde()
        self.assertEqual((614, 10), res.shape)
