import os
from unittest import TestCase

import numpy as np
import sklearn.datasets
import sklearn.model_selection
import xgboost

from causal_inference.utils.spark_random_search_cv import \
    SparkRandomizedSearchCV


class TestSparkRandomizedSearchCV(TestCase):
    def test_classification(self):
        if not os.environ.get('SPARK_HOME'):
            pass

        from pyspark.sql import SparkSession
        spark = SparkSession.builder.appName('Test').getOrCreate()
        sc = spark.sparkContext

        # Expected: SparkRandomizedSearchCV == RandomizedSearchCV
        x, y = sklearn.datasets.make_classification(n_samples=100,
                                                    n_features=5,
                                                    random_state=42)
        x_train, x_test, y_train, y_test = \
            sklearn.model_selection.train_test_split(x, y,
                                                     test_size=0.1,
                                                     random_state=42)

        clf = xgboost.XGBClassifier()
        param_distributions = {
            'n_estimators': [5],
            'max_depth': [2, 3],
            'learning_rate': [0.001, 0.01, 0.1, 1],
            'n_jobs': [1]
        }

        fit_params = {
            'eval_metric': 'auc',
            'eval_set': [[x_test, y_test]],
            'verbose': False
        }

        rs_clf1 = SparkRandomizedSearchCV(sc,
                                          clf,
                                          param_distributions,
                                          cv=3,
                                          iid=True,
                                          n_iter=5,
                                          random_state=42)
        rs_clf1.fit(x_train, y=y_train, **fit_params)
        y_test_proba1 = rs_clf1.predict_proba(x_test)[:, 1]

        rs_clf2 = sklearn.model_selection.RandomizedSearchCV(
            clf,
            param_distributions,
            cv=3,
            iid=True,
            n_iter=5,
            random_state=42)
        rs_clf2.fit(x_train, y=y_train, **fit_params)
        y_test_proba2 = rs_clf2.predict_proba(x_test)[:, 1]

        self.assertDictEqual(rs_clf1.best_params_, rs_clf2.best_params_)
        self.assertAlmostEqual(rs_clf1.best_score_, rs_clf2.best_score_)
        np.testing.assert_array_almost_equal(y_test_proba1, y_test_proba2)
