from collections import OrderedDict

import gc
from rpy2.robjects import numpy2ri
from rpy2.robjects.packages import importr

from .base import CausalEstimatorBase

numpy2ri.activate()


class BayesianAdditiveRegressionTrees(CausalEstimatorBase):
    def __init__(self, dataset):
        if len(dataset.outcomes) > 1:
            raise AssertionError('BART deals with one outcome.')
        super(BayesianAdditiveRegressionTrees, self).__init__(dataset)

    def do_all(self,
               estimand_list,
               method_resp="bart",
               p_score_as_covariate=True,
               method_name="BART"):
        results = OrderedDict()

        # Import R packages.
        bart_cause = importr("bartCause")
        base = importr("base")

        propensity = self.compute_propensity_score()

        # Convert treatment and covariates to R objects.
        outcome = self._dataset.outcomes[0]

        # Initialize the treatment effect table.
        results['ate_table'] = self._get_empty_ate_table()

        # BART
        for estimand in estimand_list:
            bart_model = bart_cause.bartc(
                response=self._dataset.get_ri_outcome(outcome),
                treatment=self._dataset.get_ri_treatment(),
                confounders=self._dataset.get_ri_covariates(),
                method_resp=method_resp,
                method_trt=numpy2ri.numpy2ri(propensity),
                estimand=str.lower(estimand),
                verbose=False,
                p_scoreAsCovariate=p_score_as_covariate,
                keepCall=False,
                **{'n.threads': '1'})
            effect, se, ci_lower, ci_upper = numpy2ri.ri2py_list(
                base.summary(bart_model).rx2('estimates'))[0]
            self._update_ate_table(results['ate_table'], outcome, method_name,
                                   estimand, effect, se, ci_lower, ci_upper)

        # Explicit garbage collection.
        gc.collect()

        # Print and return.
        print(results['ate_table'].to_string())
        return results
