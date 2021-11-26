from itertools import islice
from itertools import product

import numpy as np
from sklearn.base import is_classifier, clone
from sklearn.metrics.scorer import check_scoring
from sklearn.model_selection import ParameterSampler
from sklearn.model_selection import RandomizedSearchCV
from sklearn.model_selection import check_cv
from sklearn.model_selection._validation import _fit_and_score
from sklearn.utils.validation import indexable


class SparkRandomizedSearchCV(RandomizedSearchCV):
    # pylint: disable=too-many-arguments
    def __init__(self,
                 sc,
                 estimator,
                 param_distributions,
                 n_iter=10,
                 scoring=None,
                 n_jobs=None,
                 iid='deprecated',
                 refit=True,
                 cv=None,
                 verbose=0,
                 pre_dispatch='2*n_jobs',
                 random_state=None,
                 error_score=np.nan,
                 return_train_score=False):

        assert cv is not None
        assert scoring is None or isinstance(scoring, str)

        super().__init__(estimator=estimator,
                         param_distributions=param_distributions,
                         n_iter=n_iter,
                         scoring=scoring,
                         n_jobs=n_jobs,
                         iid=iid,
                         refit=refit,
                         cv=cv,
                         verbose=verbose,
                         pre_dispatch=pre_dispatch,
                         random_state=random_state,
                         error_score=error_score,
                         return_train_score=return_train_score)

        self.sc = sc
        self.cv_results_ = None
        self.best_index_ = None
        self.best_score_ = None
        self.best_params_ = None
        self.best_estimator_ = None

    def _run_search(self, evaluate_candidates):
        pass

    def evaluate_candidates(self, x, y, groups, candidate_params, scorers,
                            fit_params):
        fit_and_score_kwargs = dict(scorer=scorers,
                                    fit_params=fit_params,
                                    return_train_score=self.return_train_score,
                                    return_n_test_samples=True,
                                    return_times=True,
                                    return_parameters=False,
                                    error_score=self.error_score,
                                    verbose=self.verbose)

        cv = check_cv(self.cv, y, classifier=is_classifier(self.estimator))
        n_splits = cv.get_n_splits(x, y, groups)

        if self.verbose > 0:
            print("Fitting {0} folds for each of {1} candidates, totalling"
                  " {2} fits".format(n_splits, len(candidate_params),
                                     len(candidate_params) * n_splits))

        param_grid = list(product(candidate_params, range(n_splits)))
        par_param_grid = self.sc.parallelize(
            list(zip(range(len(param_grid)), param_grid)), len(param_grid))

        x_bc = self.sc.broadcast(x)
        y_bc = self.sc.broadcast(y)
        groups_bc = self.sc.broadcast(groups)
        base_estimator = self.estimator

        def test_one_parameter(task):
            (index, (parameters, split_idx)) = task
            local_estimator = clone(base_estimator)
            local_x = x_bc.value
            local_y = y_bc.value
            local_groups = groups_bc.value

            train, test = next(
                islice(cv.split(local_x, local_y, local_groups), split_idx,
                       split_idx + 1))
            res = _fit_and_score(local_estimator,
                                 local_x,
                                 local_y,
                                 train=train,
                                 test=test,
                                 parameters=parameters,
                                 **fit_and_score_kwargs)

            return index, res

        out = dict(par_param_grid.map(test_one_parameter).collect())
        x_bc.unpersist()
        y_bc.unpersist()
        groups_bc.unpersist()

        out = [out[idx] for idx in range(len(param_grid))]

        # Warning: may not work for sklearn != 0.20.3
        results = self._format_results(candidate_params, scorers, n_splits,
                                       out)
        return results

    # noinspection PyPep8Naming
    def fit(self, X, y=None, groups=None, **fit_params):
        # pylint: disable=unbalanced-tuple-unpacking
        X, y, groups = indexable(X, y, groups)

        # Evaluate candidates.
        scorers = {
            "score": check_scoring(self.estimator, scoring=self.scoring)
        }
        candidate_params = list(
            ParameterSampler(self.param_distributions,
                             self.n_iter,
                             random_state=self.random_state))
        self.cv_results_ = self.evaluate_candidates(X, y, groups,
                                                    candidate_params, scorers,
                                                    fit_params)

        # Get the best parameter.
        self.best_index_ = self.cv_results_["rank_test_score"].argmin()
        self.best_score_ = self.cv_results_["mean_test_score"][
            self.best_index_]
        self.best_params_ = self.cv_results_["params"][self.best_index_]

        # Refit.
        if self.refit:
            best_estimator = clone(
                self.estimator).set_params(**self.best_params_)
            if y is not None:
                best_estimator.fit(X, y, **fit_params)
            else:
                best_estimator.fit(X, **fit_params)
            self.best_estimator_ = best_estimator

        return self
