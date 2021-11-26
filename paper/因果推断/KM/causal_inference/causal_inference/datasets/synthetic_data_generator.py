# Datasets are generated according to Section 1 of [1].
# References
# [1] Pham, T.T. 2017. Large Scale Causal Inference with Machine Learning. Stanford.

import math
import numpy as np
import pandas as pd


def generate_covariates(num_samples, num_covariates, covariates_type):
    if covariates_type in ("independence", "dependence"):
        mean = np.zeros(num_covariates)
        cov = np.ones((num_covariates, num_covariates))
        if covariates_type == "dependence":
            for i in range(0, num_covariates):
                for j in range(0, num_covariates):
                    cov[i, j] = 2**(-abs(i - j))
        x = np.random.multivariate_normal(mean, cov, size=num_samples)
        y = np.zeros(num_samples)
    elif covariates_type == 'clustering':
        mean = np.zeros(num_covariates)
        cov = np.ones((num_covariates, num_covariates))
        centers = np.random.multivariate_normal(mean, cov, size=10)
        y = np.random.choice(np.arange(0, 10), num_samples)
        # pylint: disable=not-an-iterable, unsubscriptable-object
        # (false positive pylint complaints)
        x = np.vstack([
            np.random.multivariate_normal(centers[i], cov, size=1) for i in y
        ])
    else:
        raise ValueError('Unknown type {}'.format(covariates_type))
    return x, y


def generate_treatment(num_samples, num_covariates, covariates_type, x, y,
                       treatment_density, treatment_model):
    treat = dict()

    if covariates_type == 'clustering':
        treat['pscore'] = np.array([0.15 if e < 5 else 0.85 for e in y])
    else:
        if treatment_density == 'dense':
            beta_w = np.arange(1, num_covariates + 1)**(-0.5)
        elif treatment_density == 'sparse':
            num_ones = min(10, num_covariates)
            beta_w = np.concatenate(
                [np.ones(num_ones),
                 np.zeros(num_covariates - num_ones)])
        elif treatment_density == 'extremely sparse':
            num_ones = 1
            beta_w = np.concatenate(
                [np.ones(num_ones),
                 np.zeros(num_covariates - num_ones)])
        else:
            raise ValueError(
                'Unknown treatment_density {}'.format(treatment_density))

        if treatment_model == 'linear':
            epsilon = np.random.normal(size=num_samples)
            tmp = np.dot(x, beta_w) + epsilon
            treat['pscore'] = 1 / (1 + (np.exp(-tmp)))
        elif treatment_model == 'nonlinear':
            tmp = np.dot(x, beta_w)
            treat['pscore'] = np.array(
                [1 - 1 / ((1 + math.exp(x))**1.23) for x in tmp])
        elif treatment_model == 'double effects':
            treat['theta'] = 0.89 * np.log(1 +
                                           np.exp(-2 - 2 * np.dot(x, beta_w)))
            treat['pscore'] = 1 - np.exp(-treat['theta'])
        else:
            raise ValueError(
                'Unknown treatment_model {}'.format(treatment_model))

    print('Average propensity score: {:.2f}'.format(treat['pscore'].mean()))
    treat['treat'] = np.random.binomial(1, treat['pscore'])

    return treat


def generate_outcome(num_samples, num_covariates, x, treat, outcome_density,
                     outcome_model):
    if outcome_density == 'dense':
        beta = np.ones(num_covariates)
    elif outcome_density == 'sparse':
        beta = 1 / np.arange(1, num_covariates + 1)**2
    else:
        raise ValueError('Unknown outcome_density {}'.format(outcome_density))

    x_beta = np.dot(x, beta)
    noise = np.random.normal(size=num_samples)
    if outcome_model == 'linear':
        y0 = x_beta + noise
        y1 = y0 + 10
    elif outcome_model == 'partially linear':
        y0 = 2 / (1 + np.exp(x_beta)) + noise
        y1 = y0 + 10
    elif outcome_model == 'nonlinear':
        y0 = -1 / (1 + np.exp(x_beta)) + noise
        y1 = 1 / (1 + np.exp(x_beta)) + noise
    elif outcome_model == 'mixed':
        y0 = -1 / (1 + np.exp(x_beta)) + x_beta + noise
        y1 = 1 / (1 + np.exp(x_beta)) + x_beta + noise
    elif outcome_model == 'double effects':
        y0 = x_beta + -1 * treat['theta'] / 2 + noise
        y1 = x_beta + 1 * treat['theta'] / 2 + noise
    else:
        raise ValueError('Unknown outcome_model {}'.format(outcome_model))

    y = np.array([x[x[2]] for x in zip(y0, y1, treat['treat'])])
    ate_oracle = np.mean(y1) - np.mean(y0)
    att_oracle = np.mean(
        [x[1] - x[0] for x in zip(y0, y1, treat['treat']) if x[2] == 1])
    atc_oracle = np.mean(
        [x[1] - x[0] for x in zip(y0, y1, treat['treat']) if x[2] == 0])
    oracle = pd.DataFrame({
        'Estimand': ['ATE', 'ATT', 'ATC'],
        'Oracle': [ate_oracle, att_oracle, atc_oracle]
    })
    return y, oracle


def generate_datasets(num_samples,
                      num_covariates,
                      covariates_type,
                      treatment_density,
                      treatment_model,
                      outcome_density_list,
                      outcome_model_list,
                      random_state=42):
    np.random.seed(random_state)

    # Covariates
    x, y = generate_covariates(num_samples, num_covariates, covariates_type)
    covariates = ["cov" + str(i) for i in range(0, num_covariates)]
    data = pd.DataFrame(x, columns=covariates)

    # Treatment
    ret_treatment = generate_treatment(num_samples, num_covariates,
                                       covariates_type, x, y,
                                       treatment_density, treatment_model)
    treat_name = "treatment"
    data[treat_name] = ret_treatment['treat']

    # Outcomes
    outcome_names = []
    oracle = pd.DataFrame(columns=['Outcome', 'Estimand', 'Oracle'])
    for outcome_model in outcome_model_list:
        for outcome_density in outcome_density_list:
            outcome_name = 'outcome_' + outcome_density + '_' + outcome_model
            outcome_names.append(outcome_name)
            data[outcome_name], oracle_tmp = \
                generate_outcome(
                    num_samples, num_covariates, x, ret_treatment,
                    outcome_density, outcome_model)
            oracle_tmp['Outcome'] = outcome_name
            oracle = oracle.append(oracle_tmp, sort=False)

    return data, covariates, treat_name, outcome_names, oracle
