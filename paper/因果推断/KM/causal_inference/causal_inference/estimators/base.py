import datetime
import time

import numpy as np
import pandas as pd
from rpy2.robjects import FloatVector
from rpy2.robjects import pandas2ri
from rpy2.robjects.packages import importr
from statsmodels.stats.weightstats import DescrStatsW

from .utils import get_timestamp
from .utils import xgb_classification

pandas2ri.activate()


class CausalEstimatorBase:
    def __init__(self, dataset, spark_context=None):
        self._dataset = dataset
        self._start_timestamp = get_timestamp()
        self._spark_context = spark_context
        print("Data size: {}".format(dataset.data.shape[0]))

    @staticmethod
    def _get_empty_ate_table():
        ate_table = pd.DataFrame(columns=[
            'Outcome', 'Method', 'Estimand', 'Estimate', 'Std. Err.',
            'Lower CI (95%)', 'Upper CI (95%)', 'Remarks'
        ])
        return ate_table

    @staticmethod
    def _update_ate_table(ate_table,
                          outcome,
                          method_name,
                          estimand,
                          estimate,
                          se,
                          ci_lower,
                          ci_upper,
                          remarks=None):
        if not remarks:
            remarks = ''
        ate_table.loc[len(ate_table)] = [
            outcome, method_name, estimand, estimate, se, ci_lower, ci_upper,
            remarks
        ]

    def _get_ate_table(self,
                       method_name,
                       estimand,
                       data=None,
                       regress_on_covariates=False,
                       weights=None,
                       remarks=None):
        if not remarks:
            remarks = ''
        start_time = time.time()

        ate_table = self._get_empty_ate_table()

        if data is None:
            data = self._dataset.data

        if weights is None:
            weights = np.ones_like(data[self._dataset.treat].values)

        survey = importr("survey")
        stats = importr("stats")
        base = importr("base")

        survey_design = survey.svydesign(ids=stats.formula("~1"),
                                         weights=FloatVector(weights),
                                         data=pandas2ri.py2ri(data))
        print('Time elapsed (preparation): {:.2f} seconds [@{}]'.format(
            time.time() - start_time,
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        for outcome in self._dataset.outcomes:
            outcome_fml = self._dataset.get_ri_outcome_formula(
                outcome, add_covariates=regress_on_covariates)
            fit = survey.svyglm(formula=outcome_fml, design=survey_design)
            ci_lower, ci_upper = stats.confint(fit, self._dataset.treat, 0.95)
            ate_table.loc[len(ate_table)] = [
                outcome,
                method_name,
                estimand,
                # estimate
                stats.coef(fit).rx2(self._dataset.treat)[0],
                # standard error
                base.sqrt(base.diag(stats.vcov(fit))).rx2(self._dataset.treat)
                [0],
                ci_lower,
                ci_upper,
                remarks
            ]
            print('Time elapsed (one outcome): {:.2f} seconds [@{}]'.format(
                time.time() - start_time,
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        return ate_table

    def compute_propensity_score(self, random_state=42):
        if not self._dataset.has_propensity_score():
            x = self._dataset.get_covariates()
            y = self._dataset.get_treatment().values
            model = xgb_classification(x,
                                       y,
                                       spark_context=self._spark_context,
                                       n_iter=20,
                                       random_state=random_state)
            propensity = model.predict_proba(x)[:, 1]
            self._dataset.add_propensity_score(propensity)
        return self._dataset.get_propensity_score()

    def _get_balance_table(self, estimand, w_adjusted=None):
        def balance_stat(value, w):
            stats0 = DescrStatsW(value[t == 0], weights=w[t == 0], ddof=0)
            stats1 = DescrStatsW(value[t == 1], weights=w[t == 1], ddof=0)
            diff = stats1.mean - stats0.mean
            if estimand == 'ATE':
                smd = diff / np.sqrt(stats1.std**2 / 2 + stats0.std**2 / 2)
            elif estimand == 'ATT':
                smd = diff / stats1.std
            else:
                smd = diff / stats0.std
            if abs(smd) < 0.1:
                status = 'Balanced (<0.1)'
            else:
                status = 'Not Balanced (>0.1)'

            return sum(w[t == 1]), stats1.mean, stats1.std, sum(w[t == 0]), \
                   stats0.mean, stats0.std, smd, status

        t = self._dataset.get_treatment()
        x = self._dataset.get_covariates()
        w_unadjusted = np.ones_like(t, dtype=float)
        w_adjusted = pd.Series(w_adjusted)

        balance_table = pd.DataFrame(columns=[
            'Covariate',
            'Count.Treated.Adj',
            'M.Treat.Adj',
            'SD.Treat.Adj',
            'Count.Control.Adj',
            'M.Control.Adj',
            'SD.Control.Adj',
            'Diff.Adj',
            'Diff.Status.Adj',
            'Count.Treated.Un',
            'M.Treat.Un',
            'SD.Treat.Un',
            'Count.Control.Un',
            'M.Control.Un',
            'SD.Control.Un',
            'Diff.Un',
            'Diff.Status.Un',
        ])

        for covariate in self._dataset.covariates:
            balance_table.loc[len(balance_table)] = [covariate] + list(
                balance_stat(x[covariate], w_adjusted)) + list(
                    balance_stat(x[covariate], w_unadjusted))

        remarks = 'Unbalanced={0:.0%}'.format(
            sum(balance_table['Diff.Status.Adj'] == 'Not Balanced (>0.1)') /
            balance_table.shape[0])

        return balance_table, remarks
