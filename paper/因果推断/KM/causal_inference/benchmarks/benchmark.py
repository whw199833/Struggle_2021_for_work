import os
import random
import sys
import warnings

import numpy as np
import pandas as pd

from causal_inference import CausalEstimatorWrapper
from causal_inference.datasets import Dataset
from causal_inference.datasets import generate_datasets


def construct_dataset(data, covariates, treat, outcomes, max_num_users):
    sample_size = min(data.shape[0], max_num_users)
    data_sampled = data.sample(n=sample_size, random_state=42)
    return Dataset(data_sampled, covariates, treat, outcomes, sort=True)


def evaluate_synthetic():
    num_samples = int(sys.argv[3])
    num_covariates = int(sys.argv[4])
    # Prepare tasks.
    tasks = []
    for repeat in range(0, 5):
        outcome_density_list = ['dense', 'sparse']
        outcome_model_list = [
            'linear', 'partially linear', 'nonlinear', 'mixed'
        ]
        for covariate_type in ['independence', 'dependence', 'clustering']:
            for treatment_density in ['dense', 'sparse']:
                for treatment_model in ['linear', 'nonlinear']:
                    tasks.append(
                        dict(num_samples=num_samples,
                             num_covariates=num_covariates,
                             repeat=repeat,
                             covariate_type=covariate_type,
                             treatment_density=treatment_density,
                             treatment_model=treatment_model,
                             outcome_density_list=outcome_density_list,
                             outcome_model_list=outcome_model_list))
        outcome_density_list = ['dense', 'sparse']
        outcome_model_list = ['double effects']
        for covariate_type in ['independence']:
            for treatment_density in ['dense', 'sparse', 'extremely sparse']:
                for treatment_model in ['double effects']:
                    tasks.append(
                        dict(num_samples=num_samples,
                             num_covariates=num_covariates,
                             repeat=repeat,
                             covariate_type=covariate_type,
                             treatment_density=treatment_density,
                             treatment_model=treatment_model,
                             outcome_density_list=outcome_density_list,
                             outcome_model_list=outcome_model_list))

    # Evaluate.
    def run_one_inference_task(task):
        # Generate the data.
        data, covariates, treat_name, outcome_names, oracle = \
            generate_datasets(task['num_samples'], task['num_covariates'],
                              task['covariate_type'],
                              task['treatment_density'],
                              task['treatment_model'],
                              task['outcome_density_list'],
                              task['outcome_model_list'],
                              random_state=42 + task['repeat'])
        # Inference
        dataset = Dataset(data,
                          covariates,
                          treat_name,
                          outcome_names,
                          sort=True)
        ci = CausalEstimatorWrapper(CausalEstimatorWrapper.default_config)
        _, results = ci.inference(dataset)
        ate_table = pd.concat([
            result['ate_table'] for result in results if 'ate_table' in result
        ],
                              sort=False)
        for k, v in task.items():
            if k in ('outcome_density_list', 'outcome_model_list'):
                continue
            ate_table[k] = v
        ate_table = ate_table.merge(oracle,
                                    on=['Estimand', 'Outcome'],
                                    how='left',
                                    sort=True)
        return ate_table

    if SPARK_MODE:
        tasks_rdd = SPARK_CONTEXT.parallelize(tasks, numSlices=len(tasks))
        att_table_list = tasks_rdd.map(run_one_inference_task).collect()
    else:
        att_table_list = [run_one_inference_task(t) for t in tasks]

    # Write results.
    logs = pd.concat(att_table_list)
    print(logs.to_csv())


def read_aciccomp_data():
    if SPARK_MODE:
        data_file_dir = SparkFiles.getRootDirectory()
        SPARK_CONTEXT.addFile('aciccomp2016_covariates.csv')
        SPARK_CONTEXT.addFile('aciccomp2016_treat_outcome.csv')
        SPARK_CONTEXT.addFile('aciccomp2016_satt.csv')
        SPARK_CONTEXT.addFile('aciccomp2017_covariates.csv')
        SPARK_CONTEXT.addFile('aciccomp2017_treat_outcome.csv')
        SPARK_CONTEXT.addFile('aciccomp2017_satt.csv')
    else:
        data_file_dir = './data'

    data16 = {
        'X':
        pd.read_csv(os.path.join(data_file_dir,
                                 'aciccomp2016_covariates.csv')),
        't_y':
        pd.read_csv(
            os.path.join(data_file_dir, 'aciccomp2016_treat_outcome.csv')),
        'satt':
        pd.read_csv(os.path.join(data_file_dir, 'aciccomp2016_satt.csv'))
    }
    data17 = {
        'X':
        pd.read_csv(os.path.join(data_file_dir,
                                 'aciccomp2017_covariates.csv')),
        't_y':
        pd.read_csv(
            os.path.join(data_file_dir, 'aciccomp2017_treat_outcome.csv')),
        'satt':
        pd.read_csv(os.path.join(data_file_dir, 'aciccomp2017_satt.csv'))
    }
    return data16, data17


def evaluate_aciccomp(max_num_tasks):
    data16, data17 = read_aciccomp_data()

    # Prepare tasks.
    tasks = [
        dict(year=2016, param_id=a, sim_id=b)
        for a, b in np.unique(data16['t_y'][['param_id', 'sim_id']], axis=0)
        if b <= 2
    ] + [
        dict(year=2017, param_id=a, sim_id=b)
        for a, b in np.unique(data17['t_y'][['param_id', 'sim_id']], axis=0)
        if b <= 5
    ]
    if len(tasks) > max_num_tasks:
        random.seed(42)
        tasks = random.sample(tasks, max_num_tasks)

    # Evaluate.
    def extract_data(task):
        if SPARK_MODE:
            d = data16_broadcast.value if task[
                'year'] == 2016 else data17_broadcast.value
            x, t_y, satt = d['X'], d['t_y'], d['satt']
        else:
            d = data16 if task['year'] == 2016 else data17
            x, t_y, satt = d['X'], d['t_y'], d['satt']

        p_id, s_id = task['param_id'], task['sim_id']
        crt_t_y = t_y.loc[(t_y['param_id'] == p_id) & (t_y['sim_id'] == s_id),
                          ['z', 'y']].reset_index(drop=True)
        data = pd.concat([x, crt_t_y], axis=1)
        covariates = list(x.columns.values)
        att_oracle = satt.loc[(satt['param_id'] == p_id) &
                              (satt['sim_id'] == s_id), 'satt'].values[0]
        return data, covariates, 'z', ['y'], att_oracle

    def run_one_inference_task(task):
        # Generate the data.
        print(task)
        data, covariates, treat_name, outcome_names, att_oracle = \
            extract_data(task)

        dataset = Dataset(data,
                          covariates,
                          treat_name,
                          outcome_names,
                          sort=True)
        configs = CausalEstimatorWrapper.default_config.copy()
        configs['estimands'] = ['ATT']
        ci = CausalEstimatorWrapper(configs)
        _, results = ci.inference(dataset)
        att_table = pd.concat([
            result['ate_table'] for result in results if 'ate_table' in result
        ],
                              sort=False)
        for k, v in task.items():
            att_table[k] = v
        att_table['Oracle'] = att_oracle
        return att_table

    if SPARK_MODE:
        data16_broadcast = SPARK_CONTEXT.broadcast(data16)
        data17_broadcast = SPARK_CONTEXT.broadcast(data17)
        tasks_rdd = SPARK_CONTEXT.parallelize(tasks, numSlices=len(tasks))
        att_table_list = tasks_rdd.map(run_one_inference_task).collect()
    else:
        att_table_list = [run_one_inference_task(t) for t in tasks]

    # Aggregate results.
    logs = pd.concat(att_table_list)
    evaluate_aciccomp_summarize(logs)


def evaluate_aciccomp_summarize(logs):

    print('------------------------------------------------------------------')
    print('Detailed results')
    print('------------------------------------------------------------------')
    print(logs.to_csv())

    print('------------------------------------------------------------------')
    print('Summary')
    print('------------------------------------------------------------------')
    logs['Method type'] = '0-Single'
    logs['Bias'] = abs(logs['Estimate'] - logs['Oracle']) / abs(logs['Oracle'])
    logs_ensemble = logs.groupby(
        ['Outcome', 'year', 'param_id', 'sim_id', 'Oracle'],
        sort=False)['Estimate', 'Lower CI (95%)',
                    'Upper CI (95%)'].mean().reset_index()
    logs_ensemble['Method'] = 'Mean'
    logs_ensemble['Method type'] = '1-Ensemble'
    logs = logs.append(logs_ensemble, sort=False)

    # Compute errors again.
    logs['Bias'] = (logs['Estimate'] - logs['Oracle']) / abs(logs['Oracle'])
    bias = logs.groupby(['Method type', 'Method'])['Bias'].describe()[[
        'count', '25%', '50%', '75%', 'min', 'mean', 'max'
    ]]
    print('Bias = (estimate-oracle)/abs(oracle)')
    print(bias.to_csv())

    logs['coverage'] = (logs['Oracle'] > logs['Lower CI (95%)']) & (
        logs['Oracle'] < logs['Upper CI (95%)'])
    logs['interval length'] = logs['Upper CI (95%)'] - logs['Lower CI (95%)']
    coverage = logs.groupby(['Method type', 'Method'
                             ])['coverage',
                                'interval length'].mean().reset_index()
    print('Coverage = % 95% confidence interval covering the oracle')
    print(coverage.to_csv())


if __name__ == '__main__':
    warnings.filterwarnings(module='sklearn*',
                            action='ignore',
                            category=DeprecationWarning)

    if len(sys.argv) < 2:
        print('Usage: ./benchmark.py mode synthetic num_samples '
              'num_covariates')
        print('Usage: ./benchmark.py mode aciccomp max_num_tasks')
        sys.exit(-1)

    # Get parameters.
    SPARK_MODE = sys.argv[1] != 'local'

    if SPARK_MODE:
        from pyspark import SparkFiles
        from pyspark.sql import SparkSession

        SPARK_SESSION = SparkSession.builder.appName(
            'Causal Inference').getOrCreate()
        SPARK_CONTEXT = SPARK_SESSION.sparkContext

    # Evaluate.
    if sys.argv[2] == 'synthetic':
        evaluate_synthetic()
    elif sys.argv[2] == 'aciccomp':
        evaluate_aciccomp(int(sys.argv[3]))
