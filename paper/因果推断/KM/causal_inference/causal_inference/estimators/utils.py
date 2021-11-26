import datetime
import time
import warnings

import numpy as np
import scipy.stats
import sklearn
import xgboost as xgb


def get_timestamp():
    return datetime.datetime.now().strftime('%Y%m%d%H%M%S')


def is_binary(arr):
    if isinstance(arr, list):
        arr = np.array(arr)
    return len(arr) == (sum(arr == 0) + sum(arr == 1))


def get_mean_se_confint(a, confidence=0.95):
    n = len(a)
    m, se = np.mean(a), scipy.stats.sem(a)
    h = se * scipy.stats.t.ppf((1 + confidence) / 2., n - 1)
    return m, se, m - h, m + h


def xgb_classification(x_fit,
                       y_fit,
                       spark_context=None,
                       n_iter=10,
                       random_state=42):
    x_train, x_test, y_train, y_test = \
        sklearn.model_selection.train_test_split(x_fit, y_fit,
                                                 test_size=0.1,
                                                 random_state=random_state)

    clf = xgb.XGBClassifier()
    param_distributions = {
        'n_estimators': [1000],
        'max_depth': [3, 4, 5],
        'learning_rate': [1e-3, 1e-2, 1e-1, 0.5, 1.],
        'subsample': np.arange(0.5, 1.01, 0.1),
        'min_child_weight': range(1, 21),
        'n_jobs': [1]
    }

    print("Randomized search..")
    search_time_start = time.time()
    fit_params = {
        'early_stopping_rounds': 10,
        'eval_metric': 'auc',
        'verbose': False,
        'eval_set': [[x_test, y_test]]
    }
    if spark_context is not None:
        from ..utils.spark_random_search_cv import SparkRandomizedSearchCV
        rs_clf = SparkRandomizedSearchCV(spark_context,
                                         clf,
                                         param_distributions,
                                         cv=3,
                                         n_iter=n_iter,
                                         random_state=random_state)
        rs_clf.fit(x_train, y=y_train, **fit_params)
    else:
        rs_clf = sklearn.model_selection.RandomizedSearchCV(
            clf,
            param_distributions,
            cv=3,
            n_iter=n_iter,
            random_state=random_state)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore",
                                    module='sklearn*',
                                    category=DeprecationWarning)
            rs_clf.fit(x_train, y_train, **fit_params)
        print("Best params:", rs_clf.best_params_)
        print("Best score:", rs_clf.best_score_)

    y_train_scores = rs_clf.predict_proba(x_train)[:, 1]
    print("AUC (train): ",
          sklearn.metrics.roc_auc_score(y_train, y_train_scores))
    y_test_scores = rs_clf.predict_proba(x_test)[:, 1]
    print("AUC (test): ", sklearn.metrics.roc_auc_score(y_test, y_test_scores))
    print("Randomized search time:", time.time() - search_time_start)

    return rs_clf


def xgb_regression(x_fit,
                   y_fit,
                   spark_context=None,
                   n_iter=10,
                   random_state=42):
    x_train, x_test, y_train, y_test = \
        sklearn.model_selection.train_test_split(x_fit, y_fit,
                                                 test_size=0.1,
                                                 random_state=random_state)

    reg = xgb.XGBRegressor()
    param_distributions = {
        'n_estimators': [1000],
        'max_depth': [3, 4, 5],
        'learning_rate': [1e-3, 1e-2, 1e-1, 0.5, 1.],
        'subsample': np.arange(0.5, 1.01, 0.1),
        'min_child_weight': range(1, 21),
        'n_jobs': [1]
    }
    print("Randomized search..")
    search_time_start = time.time()
    fit_params = {
        'early_stopping_rounds': 10,
        'eval_metric': 'rmse',
        'verbose': False,
        'eval_set': [[x_test, y_test]]
    }
    if spark_context is not None:
        from ..utils.spark_random_search_cv import SparkRandomizedSearchCV
        rs_reg = SparkRandomizedSearchCV(spark_context,
                                         reg,
                                         param_distributions,
                                         cv=3,
                                         n_iter=n_iter,
                                         random_state=random_state)
        rs_reg.fit(x_train, y=y_train, **fit_params)
    else:
        rs_reg = sklearn.model_selection.RandomizedSearchCV(
            reg,
            param_distributions,
            cv=3,
            n_iter=n_iter,
            random_state=random_state)

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore",
                                    module='sklearn*',
                                    category=DeprecationWarning)
            rs_reg.fit(x_train, y=y_train, **fit_params)
        print("Best params:", rs_reg.best_params_)
        print("Best score:", rs_reg.best_score_)

    y_test_scores = rs_reg.predict(x_test)
    print("RMSE: ", sklearn.metrics.mean_absolute_error(y_test, y_test_scores))
    print("Randomized search time:", time.time() - search_time_start)

    return rs_reg
