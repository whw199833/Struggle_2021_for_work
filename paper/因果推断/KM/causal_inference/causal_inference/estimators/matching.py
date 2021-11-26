import bisect
import random
from collections import OrderedDict

import numpy as np

from .base import CausalEstimatorBase


class Matching(CausalEstimatorBase):
    def __init__(self, dataset, spark_context=None):
        super(Matching, self).__init__(dataset, spark_context=spark_context)

    def do_all(self, estimand_list, random_seed=42):
        results = OrderedDict()

        if 'ATT' not in estimand_list:
            # TODO: support ATE and ATC
            return results

        # Get the matched data.
        data_matched, weights = self.get_data_matched(random_seed)

        # Get the balance table.
        results['balance_table_({})'.format(
            'ATT')], remarks = self._get_balance_table(estimand='ATT',
                                                       w_adjusted=weights)

        # Estimate the ATT.
        ate_table = self._get_ate_table("Propensity Score Matching",
                                        'ATT',
                                        data=data_matched.data,
                                        remarks=remarks)
        results['ate_table'] = ate_table

        # Print and return.
        print(results['ate_table'].to_string())
        return results

    def get_data_matched(self, random_seed=42):
        # Estimate the propensity score.
        propensity = self.compute_propensity_score(random_state=random_seed)

        best_caliper = ''
        best_smd = self._get_mean_smd(self._dataset.data)
        best_matched_idx = self._dataset.data.index

        for caliper_method in ['logit', 'propensity']:
            for caliper_threshold in [
                    0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5
            ]:
                matches = self._match(propensity, caliper_threshold,
                                      caliper_method, random_seed)
                idx = list(matches.keys()) + list(matches.values())
                smd = self._get_mean_smd(self._dataset.data.loc[idx, :])
                if smd < best_smd:
                    best_smd = smd
                    best_matched_idx = list(matches.keys()) + list(
                        matches.values())
                    best_caliper = '{} ({})'.format(caliper_method,
                                                    caliper_threshold)

        print('Best caliper: ' + best_caliper)

        data_matched = self._dataset.subset(
            best_matched_idx, False)  # with the propensity score removed
        weights = np.zeros(self._dataset.get_treatment().shape)
        weights[idx] = 1
        return data_matched, weights

    def _match(self, propensity, caliper_threshold, caliper_method,
               random_seed):
        groups = self._dataset.data[self._dataset.treat]

        # Transform the propensity scores.
        if caliper_method == 'logit':
            propensity = propensity.clip(1e-6, 1 - 1e-6)
            propensity_transformed = np.log(propensity / (1 - propensity))
            caliper_threshold = caliper_threshold * np.std(
                propensity_transformed)
        else:
            propensity_transformed = propensity

        # Prepare propensity scores and indices.
        treat_combined = list(
            zip(propensity_transformed[groups == 1],
                groups[groups == 1].index))
        random.seed(random_seed + 1)
        random.shuffle(treat_combined)
        treat_ps, treat_idx = [list(x) for x in zip(*treat_combined)]

        control_combined = list(
            zip(propensity_transformed[groups == 0],
                groups[groups == 0].index))
        random.seed(random_seed + 2)
        random.shuffle(control_combined)
        control_combined.sort(key=lambda tup: tup[0])
        control_ps, control_idx = [list(x) for x in zip(*control_combined)]

        # Propensity score matching.
        matches = {}
        for i in np.arange(0, len(treat_ps)):
            # Find the nearest control unit.
            treat_ps_current = treat_ps[i]
            idx, dist = self._find_nearest_neighbor(treat_ps_current,
                                                    control_ps)

            # Update the match results.
            if (dist <= caliper_threshold) or caliper_threshold == 0:
                matches[treat_idx[i]] = control_idx[idx]
                # Remove the control unit if we are matching without the replacement.
                del control_idx[idx], control_ps[idx]

            # Early break if there is no control unit left.
            if not control_ps:
                break

        return matches

    def _get_mean_smd(self, data):
        groups = data[self._dataset.treat]
        data_groups = data.groupby(groups)[self._dataset.covariates]
        means = data_groups.mean()
        diff = abs(means.diff()).iloc[1]
        std = data_groups.std()
        smd = diff / std.apply(lambda s: np.sqrt(s[0]**2 / 2 + s[1]**2 / 2))
        return smd.abs().mean()

    @staticmethod
    def _find_nearest_neighbor(target, sorted_arr):
        # Find the nearest control unit.
        num_control = len(sorted_arr)
        idx_right = min(num_control - 1,
                        bisect.bisect_left(sorted_arr,
                                           target))  # first position >= X
        idx_left = max(0, idx_right - 1)
        dist_left = abs(sorted_arr[idx_left] - target)
        dist_right = abs(sorted_arr[idx_right] - target)
        if dist_left <= dist_right:
            idx, dist = idx_left, dist_left
        else:
            idx, dist = idx_right, dist_right
        return idx, dist
