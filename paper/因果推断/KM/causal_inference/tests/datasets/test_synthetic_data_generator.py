from unittest import TestCase

from causal_inference.datasets.synthetic_data_generator import generate_datasets


class TestSyntheticDataGenerator(TestCase):
    def test_generate_datasets(self):
        n_rows = 100
        n_cols = 10

        # General cases.
        outcome_model_list = [
            'linear', 'partially linear', 'nonlinear', 'mixed'
        ]
        outcome_density_list = ['dense', 'sparse']
        for covariate_type in ['independence', 'dependence', 'clustering']:
            for treatment_density in ['dense', 'sparse']:
                for treatment_model in ['linear', 'nonlinear']:
                    data, covariates, treat_name, outcome_names, oracle = \
                        generate_datasets(n_rows, n_cols,
                                          covariate_type,
                                          treatment_density, treatment_model,
                                          outcome_density_list,
                                          outcome_model_list)
                    self.assertEqual(n_rows, data.shape[0])
                    self.assertEqual(n_cols, len(covariates))
                    self.assertIsNotNone(outcome_names)
                    self.assertEqual(len(outcome_names) * 3, len(oracle))
                    self.assertIn(treat_name, data.columns)
                    for c in covariates:
                        self.assertIn(c, data.columns)

        # Double effects.
        outcome_model_list = ['double effects']
        outcome_density_list = ['dense', 'sparse']
        for covariate_type in ['independence']:
            for treatment_density in ['dense', 'sparse', 'extremely sparse']:
                for treatment_model in ['double effects']:
                    data, covariates, treat_name, outcome_names, oracle = \
                        generate_datasets(n_rows, n_cols,
                                          covariate_type,
                                          treatment_density, treatment_model,
                                          outcome_density_list,
                                          outcome_model_list)
                    self.assertEqual(n_rows, data.shape[0])
                    self.assertEqual(n_cols, len(covariates))
                    self.assertIsNotNone(outcome_names)
                    self.assertEqual(len(outcome_names) * 3, len(oracle))
                    self.assertIn(treat_name, data.columns)
                    for c in covariates:
                        self.assertIn(c, data.columns)
