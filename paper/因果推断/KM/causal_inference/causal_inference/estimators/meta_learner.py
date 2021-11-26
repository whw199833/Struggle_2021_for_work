import random
from collections import OrderedDict

import numpy as np
import pandas as pd
import sklearn.linear_model
from sklearn.model_selection import RandomizedSearchCV
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor, XGBClassifier

from .base import CausalEstimatorBase
from .utils import get_mean_se_confint, is_binary


def search_parameters(estimator, x, y, sample_weight=None):
    if x.shape[0] > 10000:
        return estimator.get_params()

    if x.shape[0] > 1000:
        n_iter = 10
        cv = 3
    else:
        n_iter = 20
        cv = 5

    param_distribution = {
        'n_estimators': [50, 100, 200],
        'eta': [0.001, 0.01, 0.1, 1],
        'max_depth': [3, 4, 5, 6],
        'min_child_weight': [1, 5, 10],
        'n_jobs': [-1],
    }
    rs = RandomizedSearchCV(estimator,
                            param_distribution,
                            n_jobs=1,
                            cv=cv,
                            n_iter=n_iter,
                            refit=False,
                            random_state=42)
    rs.fit(x, y, sample_weight=sample_weight)
    return rs.best_params_


class ClassificationLearner:
    def __init__(self, **kwargs):
        self.estimator = XGBClassifier(**kwargs)
        self.fit_info = None

    # noinspection PyPep8Naming
    # pylint: disable-msg=too-many-arguments
    # pylint: disable-msg=too-many-locals
    # pylint: disable-msg=invalid-name
    def fit(self, X, y):
        # If there is no evaluation data, split some.
        x_train, x_test, y_train, y_test = train_test_split(X,
                                                            y,
                                                            test_size=0.1,
                                                            random_state=42)

        if X.shape[0] < 10000:
            best_param = search_parameters(self.estimator, x_train, y_train)
            self.estimator.set_params(**best_param)

        self.estimator.fit(x_train,
                           y_train,
                           eval_set=[(x_test, y_test)],
                           early_stopping_rounds=10,
                           verbose=False)

        y_train_pred = self.predict_proba(x_train)[:, 1]
        train_auc = sklearn.metrics.roc_auc_score(y_train, y_train_pred)
        y_test_pred = self.predict_proba(x_test)[:, 1]
        test_auc = sklearn.metrics.roc_auc_score(y_test, y_test_pred)

        self.fit_info = 'Train/Test AUC: {:.2f}/{:.2f}'.format(
            train_auc, test_auc)

        return self

    def predict_proba(self, x):
        return self.estimator.predict_proba(x)

    def predict(self, x):
        return self.estimator.predict(x)


class RegressionLearner:
    def __init__(self, **kwargs):
        self.estimator = XGBRegressor(**kwargs)
        self.fit_info = None

    # noinspection PyPep8Naming
    # pylint: disable-msg=too-many-arguments
    # pylint: disable-msg=too-many-locals
    # pylint: disable-msg=invalid-name
    def fit(self, X, y):
        # If there is no evaluation data, split some.
        x_train, x_test, y_train, y_test = train_test_split(X,
                                                            y,
                                                            test_size=0.1,
                                                            random_state=42)

        if X.shape[0] < 10000:
            best_param = search_parameters(self.estimator, x_train, y_train)
            self.estimator.set_params(**best_param)

        self.estimator.fit(x_train,
                           y_train,
                           eval_set=[(x_test, y_test)],
                           early_stopping_rounds=10,
                           verbose=False)

        y_train_pred = self.predict(x_train)
        train_r2 = sklearn.metrics.r2_score(y_train, y_train_pred)
        y_test_pred = self.predict(x_test)
        test_r2 = sklearn.metrics.r2_score(y_test, y_test_pred)

        self.fit_info = 'Train/Test R2: {:.2f}/{:.2f}'.format(
            train_r2, test_r2)

        return self

    def predict(self, x):
        return self.estimator.predict(x)


class MetaLearner(CausalEstimatorBase):
    def do_all(self,
               estimand_list,
               method,
               pscore_as_covariate,
               random_state=42):
        np.random.seed(random_state)
        random.seed(random_state)

        if not self._dataset.has_propensity_score():
            ps = self.compute_propensity_score(random_state=random_state)
            self._dataset.add_propensity_score(ps)

        # Prepare results.
        results = OrderedDict()
        results['ate_table'] = self._get_empty_ate_table()
        results['ml_metrics'] = pd.DataFrame(
            columns=['Outcome', 'Fitted target', 'User group', 'Remarks'])

        # Prepare propensity score, X, treatment
        ps = np.array(self._dataset.get_propensity_score())
        x = np.array(
            self._dataset.get_covariates(add_pscore=pscore_as_covariate))
        t = np.array(self._dataset.get_treatment())

        for outcome in self._dataset.outcomes:
            y = np.array(self._dataset.get_outcome(outcome))

            if is_binary(y):
                model_mu0 = ClassificationLearner(random_state=42)
                model_mu1 = ClassificationLearner(random_state=42)
                model_tau0 = RegressionLearner(random_state=42)
                model_tau1 = RegressionLearner(random_state=42)
            else:
                model_mu0 = RegressionLearner(random_state=42)
                model_mu1 = RegressionLearner(random_state=42)
                model_tau0 = RegressionLearner(random_state=42)
                model_tau1 = RegressionLearner(random_state=42)

            model_mu0.fit(x[t == 0], y[t == 0])
            model_mu1.fit(x[t == 1], y[t == 1])
            mu0 = model_mu0.predict(x)
            mu1 = model_mu1.predict(x)
            model_tau0.fit(x[t == 0], mu1[t == 0] - y[t == 0])
            model_tau1.fit(x[t == 1], y[t == 1] - mu0[t == 1])

            if 'xlearner' in method:
                te = ps * model_tau0.predict(x) + (1 -
                                                   ps) * model_tau1.predict(x)
                method_name = 'X-Learner' + ('on PScore'
                                             if pscore_as_covariate else '')
                self.update_ate_table(results, outcome, method_name,
                                      estimand_list, t, te)

            if 'mlearner' in method:
                te = (t - ps) / (ps * (1 - ps)) * (y -
                                                   (1 - ps) * mu1 - ps * mu0)
                method_name = 'M-Learner' + ('on PScore'
                                             if pscore_as_covariate else '')
                self.update_ate_table(results, outcome, method_name,
                                      estimand_list, t, te)

            results['ml_metrics'].loc[len(results['ml_metrics'])] = [
                outcome, "Y", "Control", model_mu0.fit_info
            ]
            results['ml_metrics'].loc[len(results['ml_metrics'])] = [
                outcome, "Y", "Treated", model_mu1.fit_info
            ]
            results['ml_metrics'].loc[len(results['ml_metrics'])] = [
                outcome, "Effect", "Control", model_tau0.fit_info
            ]
            results['ml_metrics'].loc[len(results['ml_metrics'])] = [
                outcome, "Effect", "Treated", model_tau1.fit_info
            ]

        print(results['ate_table'].to_string())
        return results

    def update_ate_table(self, results, outcome, method_str, estimand_list,
                         treatment, te):
        remarks = "See \"more information\" for error metrics of ML learners"
        if 'ATC' in estimand_list:
            m, se, lb, ub = get_mean_se_confint(te[treatment == 0])
            self._update_ate_table(results['ate_table'], outcome, method_str,
                                   'ATC', m, se, lb, ub, remarks)
        if 'ATT' in estimand_list:
            m, se, lb, ub = get_mean_se_confint(te[treatment == 1])
            self._update_ate_table(results['ate_table'], outcome, method_str,
                                   'ATT', m, se, lb, ub, remarks)
        if 'ATE' in estimand_list:
            m, se, lb, ub = get_mean_se_confint(te)
            self._update_ate_table(results['ate_table'], outcome, method_str,
                                   'ATE', m, se, lb, ub, remarks)
