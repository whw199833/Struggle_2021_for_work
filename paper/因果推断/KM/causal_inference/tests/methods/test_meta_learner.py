from unittest import TestCase

from causal_inference.datasets import load_builtin, Dataset
from causal_inference.estimators.meta_learner import MetaLearner


class TestMetaLearner(TestCase):
    def __init__(self, *args, **kwargs):
        data = load_builtin("lalonde")
        data["re78_positive"] = (data['re78'] > 0).astype('int')
        self.dataset = Dataset(data, [
            "age", "educ", "black", "hispan", "married", "nodegree", "re74",
            "re75"
        ],
                               "treat", ["re78", "re78_positive"],
                               sort=True)
        super(TestMetaLearner, self).__init__(*args, **kwargs)

    def test_all_meta_learner(self):
        estimator = MetaLearner(self.dataset)
        results = estimator.do_all(['ATE', 'ATT', 'ATC'],
                                   ['xlearner', 'mlearner'], False)
        self.assertTrue('ate_table' in results)
        self.assertGreater(results['ate_table'].shape[0], 0)
        print(results['ml_metrics'])
