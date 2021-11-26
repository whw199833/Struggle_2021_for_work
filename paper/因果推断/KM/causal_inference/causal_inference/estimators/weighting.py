import datetime
import gc
import time
from collections import OrderedDict

import empirical_calibration as ec
import numpy as np
from rpy2.robjects.packages import importr

from .base import CausalEstimatorBase


class Weighting(CausalEstimatorBase):
    def __init__(self, dataset):
        super(Weighting, self).__init__(dataset)

    def do_all(self, estimand_list, method="ps", random_seed=42):
        # Prepare results.
        results = OrderedDict()
        results['ate_table'] = self._get_empty_ate_table()

        for estimand in estimand_list:
            start_time = time.time()

            # Get weights.
            if method == 'ec':
                weights = self._get_weights_ec(estimand)
            else:
                weights = self._get_weights_weightit(estimand, method,
                                                     random_seed)

            print('Time elapsed (get weights): {:.2f} seconds [@{}]'.format(
                time.time() - start_time,
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

            # Get the balance table.
            results['balance_table_({})'.format(
                estimand)], remarks = self._get_balance_table(
                    estimand=estimand, w_adjusted=weights)

            # Get the treatment effect.
            results['ate_table'] = results['ate_table'].append(
                self._get_ate_table("Weighting ({})".format(method),
                                    estimand,
                                    weights=weights,
                                    remarks=remarks))
            print('Time elapsed (get ate table): {:.2f} seconds [@{}]'.format(
                time.time() - start_time,
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        # Print and return.
        print(results['ate_table'].to_string())
        return results

    def _get_weights_weightit(self, estimand, method, random_seed):
        # Import R packages.
        weightit = importr("WeightIt")

        # Compute weight of each sample.
        pscore_fml = self._dataset.get_ri_treatment_formula()
        data_r_df = self._dataset.get_r_dataframe()

        if method == "ps":
            propensity = self.compute_propensity_score(random_seed)
            weights = weightit.weightit(pscore_fml,
                                        data=data_r_df,
                                        ps=propensity,
                                        estimand=estimand).rx2('weights')
        else:
            weights = weightit.weightit(
                pscore_fml,
                data=data_r_df,
                method="ps" if method == "glm" else method,
                estimand=estimand).rx2('weights')

        weights = np.array(weights)

        # Explicit garbage collection.
        gc.collect()

        weights = self._trim(estimand, weights, at=0.99)
        return weights

    def _get_weights_ec(self, estimand):
        x = self._dataset.get_covariates(add_pscore=False)
        t = self._dataset.get_treatment()
        x_treated = x[t == 1]
        x_control = x[t == 0]

        # Get weights.
        weights = np.ones(t.shape, dtype=float)
        if estimand == 'ATT':
            w0, _ = ec.maybe_exact_calibrate(covariates=x_control,
                                             target_covariates=x_treated,
                                             autoscale=True)
            weights[t == 0] = w0
        elif estimand == 'ATC':
            w1, _ = ec.maybe_exact_calibrate(covariates=x_treated,
                                             target_covariates=x_control,
                                             autoscale=True)
            weights[t == 1] = w1
        elif estimand == 'ATE':
            w1, _ = ec.maybe_exact_calibrate(covariates=x_treated,
                                             target_covariates=x,
                                             autoscale=True)
            w0, _ = ec.maybe_exact_calibrate(covariates=x_control,
                                             target_covariates=x,
                                             autoscale=True)
            weights[t == 1] = w1
            weights[t == 0] = w0

        return weights

    def _trim(self, estimand, weights, at=0.99):
        at = max(at, 1 - at)
        if at < 0 or at > 1:
            raise AssertionError('at < 0 or at > 1')

        treatment = self._dataset.get_treatment()
        if estimand == 'ATE':
            # Trim all weights.
            trim_upper = np.quantile(weights, q=at)
            trimmed_weights = weights.clip(weights, max=trim_upper)
        elif estimand == 'ATT':
            # Trim weights of control units.
            w0 = weights[treatment == 0]
            trim_upper = np.quantile(w0, q=at)
            trimmed_weights = weights.copy()
            trimmed_weights[treatment == 0] = w0.clip(max=trim_upper)
        else:
            # Trim weights of treated units.
            w1 = np.array(weights[treatment == 1])
            trim_upper = np.quantile(w1, q=at)
            trimmed_weights = weights.copy()
            trimmed_weights[treatment == 1] = w1.clip(max=trim_upper)

        print("Trimming threshold [0, {:.6f}]".format(trim_upper))
        return trimmed_weights
