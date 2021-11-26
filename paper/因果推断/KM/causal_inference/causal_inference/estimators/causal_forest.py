from collections import OrderedDict

import gc
from rpy2.robjects import pandas2ri
from rpy2.robjects.packages import importr

from .base import CausalEstimatorBase


class CausalForest(CausalEstimatorBase):
    def __init__(self, dataset):
        if len(dataset.outcomes) > 1:
            raise AssertionError('CausalForest deals with one outcome.')
        super(CausalForest, self).__init__(dataset)

    def do_all(self, estimand_list, random_state=42):

        if not self._dataset.has_propensity_score():
            ps = self.compute_propensity_score(random_state=random_state)
            self._dataset.add_propensity_score(ps)

        results = OrderedDict()

        # Import R packages.
        grf = importr('grf')

        # Initialize the treatment effect table.
        results['ate_table'] = self._get_empty_ate_table()

        # Run Causal Forest for each outcome.
        outcome = self._dataset.outcomes[0]
        tau_forest = grf.causal_forest(
            self._dataset.get_ri_covariates(),
            self._dataset.get_outcome(outcome),
            self._dataset.get_ri_treatment(),
            W_hat=self._dataset.get_ri_propensity_score(),
            num_threads=1,
            seed=random_state)

        target_sample = dict({
            'ATE': 'all',
            'ATT': 'treated',
            'ATC': 'control'
        })
        for estimand in estimand_list:
            # Extract results.
            effect, se = pandas2ri.ri2py(
                grf.average_treatment_effect(
                    tau_forest, target_sample=target_sample[estimand]))
            ci_lower = effect - 1.96 * se
            ci_upper = effect + 1.96 * se
            self._update_ate_table(results['ate_table'], outcome,
                                   'Causal Forest', estimand, effect, se,
                                   ci_lower, ci_upper)

        # Explicit garbage collection.
        gc.collect()

        # Print and return.
        print(results['ate_table'].to_string())
        return results
