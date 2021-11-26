import datetime
import time

import pandas as pd
from rpy2.robjects import r

from causal_inference.estimators.bart import BayesianAdditiveRegressionTrees
from causal_inference.estimators.base import CausalEstimatorBase
from causal_inference.estimators.causal_forest import CausalForest
from causal_inference.estimators.matching import \
    Matching
from causal_inference.estimators.weighting import \
    Weighting
from causal_inference.estimators.meta_learner import MetaLearner

from causal_inference.utils.config_parser import Converters


class CausalEstimatorWrapper:
    default_config = dict({
        'estimands': ['ATT'],
        'bart_max_num_users': 10000,
        'weighting_ps_max_num_users': 100000,
        'weighting_cbps_max_num_users': 0,
        'weighting_optweight_max_num_users': 0,
        'weighting_ec_max_num_users': 100000,
        'causalforest_max_num_users': 10000,
        'psm_max_num_users': 100000,
        'xlearner_max_num_users': 100000,
        'mlearner_max_num_users': 100000,
    })
    converter_rules = dict({
        'estimands': Converters.string_list_converter,
        'bart_max_num_users': int,
        'weighting_ps_max_num_users': int,
        'weighting_cbps_max_num_users': int,
        'weighting_optweight_max_num_users': int,
        'weighting_ec_max_num_users': int,
        'causalforest_max_num_users': int,
        'psm_max_num_users': int,
        'xlearner_max_num_users': int,
        'mlearner_max_num_users': int,
    })

    def __init__(self, config):
        # Check config
        for key in self.converter_rules:
            if key not in config:
                raise ValueError('Wrong config: {} is not set.'.format(key))
        self._args = config
        self._need_propensity_score = \
            self._args['psm_max_num_users'] > 0 or\
            self._args['bart_max_num_users'] > 0 or \
            self._args['causalforest_max_num_users'] > 0 or\
            self._args['weighting_ps_max_num_users'] > 0 or \
            self._args['weighting_ec_max_num_users'] > 0 or \
            self._args['xlearner_max_num_users'] > 0 or \
            self._args['mlearner_max_num_users'] > 0
        self._preprocess_results = None
        self._results = None
        self._start_time = None
        self._dataset = None

        r('memory.limit(size=8132)')

    def _prepare_report(self):
        def get_section_title(title):
            res = '=' * 80 + '\n'
            res += title + '\n'
            res += '=' * 80 + '\n'
            return res

        # Initialize the final report (a string).
        results = self._results
        report = ''

        if results:
            # Merge all ATT tables.
            report += get_section_title('Average treatment effect table')
            all_ate_table = pd.concat([
                result['ate_table']
                for result in results if 'ate_table' in result
            ],
                                      sort=False)
            all_ate_table['Outcome'] = \
                pd.Categorical(all_ate_table['Outcome'],
                               categories=self._dataset.outcomes,
                               ordered=True)

            for estimand in ['ATE', 'ATT', 'ATC']:
                ate_table = all_ate_table[all_ate_table.Estimand == estimand]
                if ate_table.shape[0]:
                    ate_table.sort_values(by=['Outcome', 'Method'],
                                          inplace=True)
                    report += ate_table.to_csv(line_terminator='\n',
                                               index=False) + '\n\n'

            # Stats for the preprocessing step.
            if self._preprocess_results is not None:
                report += get_section_title(
                    'Preprocess results (balance table)')
                report += self._preprocess_results.to_csv(line_terminator='\n',
                                                          index=False) + '\n\n'

            # Merge all running time tables.
            report += get_section_title('Running time')
            running_time_table = pd.concat([
                result['running_time']
                for result in results if 'running_time' in result
            ],
                                           sort=False)
            running_time_table.sort_values(by=['task_name'], inplace=True)
            report += running_time_table.to_csv(line_terminator='\n',
                                                index=False) + '\n\n'

            # Print more method-specific information.
            for result in results:
                # Skip this method if the only result is the ATT table.
                if len(result) <= 2:
                    continue
                method_name_long = '/'.join(
                    result['ate_table']['Method'].unique())
                report += get_section_title('More information of ' +
                                            method_name_long)
                for k, v in result.items():
                    if k in ('ate_table', 'running_time'):
                        continue
                    report += k + '\n'
                    if isinstance(v, str):
                        report += v + '\n\n'
                    else:
                        report += v.to_csv(line_terminator='\n',
                                           index=False) + '\n\n'

        # Backup the configurations.
        report += get_section_title('Configuration')
        for k, v in self._args.items():
            if k not in ['tdw_username', 'tdw_password']:
                report += k + ',' + str(v) + '\n'

        return report

    def _run_all_methods(self, dataset, spark_context=None):
        args = self._args

        # Prepare all inference tasks.
        outcome_names = dataset.outcomes
        tasks = list()

        if args['bart_max_num_users'] > 0:
            for outcome_name in outcome_names:
                basic_dict = dict(
                    task_name='BART_' + outcome_name,
                    max_num_users=args['bart_max_num_users'],
                    outcome_name=outcome_name,
                    method_class_name=BayesianAdditiveRegressionTrees,
                )
                d1 = dict(
                    method_do_all_args=dict(estimand_list=args['estimands'],
                                            method_resp="bart",
                                            p_score_as_covariate=False,
                                            method_name="BART"))
                d2 = dict(
                    method_do_all_args=dict(estimand_list=args['estimands'],
                                            method_resp="tmle",
                                            p_score_as_covariate=False,
                                            method_name="BART + TMLE"))
                d3 = dict(
                    method_do_all_args=dict(estimand_list=args['estimands'],
                                            method_resp="tmle",
                                            p_score_as_covariate=True,
                                            method_name="BART on PScore"))
                tasks.append({**basic_dict, **d1})
                tasks.append({**basic_dict, **d2})
                tasks.append({**basic_dict, **d3})

        if args['causalforest_max_num_users'] > 0:
            for outcome_name in outcome_names:
                tasks.append(
                    dict(task_name='CausalForest_' + outcome_name,
                         max_num_users=args['causalforest_max_num_users'],
                         outcome_name=outcome_name,
                         method_class_name=CausalForest,
                         method_do_all_args=dict(
                             estimand_list=args['estimands'])))

        for weighting_method in ['ps', 'ec', 'cbps', 'optweight']:
            n = args['weighting_{}_max_num_users'.format(weighting_method)]
            if n > 0:
                tasks.append(
                    dict(task_name='Weighting_{}'.format(
                        weighting_method.upper()),
                         max_num_users=n,
                         outcome_name=None,
                         method_class_name=Weighting,
                         method_do_all_args=dict(
                             estimand_list=args['estimands'],
                             method=weighting_method)))

        if args['psm_max_num_users'] > 0:
            tasks.append(
                dict(task_name='PSM',
                     max_num_users=args['psm_max_num_users'],
                     outcome_name=None,
                     method_class_name=Matching,
                     method_do_all_args=dict(estimand_list=args['estimands'])))

        if args['xlearner_max_num_users'] > 0 or args[
                'mlearner_max_num_users'] > 0:
            n = max(args['xlearner_max_num_users'],
                    args['mlearner_max_num_users'])
            if n > 0:
                for outcome_name in outcome_names:
                    basic_dict = dict(
                        task_name='meta_learner_' + outcome_name,
                        max_num_users=n,
                        outcome_name=outcome_name,
                        method_class_name=MetaLearner,
                    )
                    d1 = dict(method_do_all_args=dict(
                        estimand_list=args['estimands'],
                        method=['xlearner', 'mlearner'],
                        pscore_as_covariate=True))
                    d2 = dict(method_do_all_args=dict(
                        estimand_list=args['estimands'],
                        method=['xlearner', 'mlearner'],
                        pscore_as_covariate=False))
                    tasks.append({**basic_dict, **d1})
                    tasks.append({**basic_dict, **d2})

        def run_one_inference_task(task, spark_mode=False):
            method_start_time = time.time()
            if spark_mode:
                dataset_sampled = dataset_broadcast.value.sample(
                    task['max_num_users'], task['outcome_name'])
            else:
                dataset_sampled = dataset.sample(task['max_num_users'],
                                                 task['outcome_name'])
            causal_inference_model = task['method_class_name'](dataset_sampled)
            do_all_args = task['method_do_all_args']
            result = causal_inference_model.do_all(**do_all_args)
            method_end_time = time.time()
            result['running_time'] = pd.DataFrame(
                dict(task_name=[task['task_name']],
                     running_time=[method_end_time - method_start_time]))
            return result

        if not spark_context:
            results = [run_one_inference_task(t) for t in tasks]
        else:
            tasks_rdd = spark_context.parallelize(tasks, numSlices=len(tasks))
            dataset_broadcast = spark_context.broadcast(dataset)
            results = tasks_rdd.map(lambda t: run_one_inference_task(
                t, spark_mode=True)).collect()
            dataset_broadcast.unpersist()

        # Return the results and the preprocessed dataset.
        return results

    def inference(self, dataset, spark_context=None):
        self._start_time = time.time()
        self._results = []
        self._dataset = dataset

        # Compute the propensity score in advance.
        if self._need_propensity_score:
            propensity = CausalEstimatorBase(
                self._dataset,
                spark_context=spark_context).compute_propensity_score()
            self._dataset.add_propensity_score(propensity)
        print('Time elapsed (propensity score): {:.2f} seconds [@{}]'.format(
            time.time() - self._start_time,
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        # Run all method.
        self._results = self._run_all_methods(self._dataset,
                                              spark_context=spark_context)
        print('Time elapsed (inference): {:.2f} seconds [@{}]'.format(
            time.time() - self._start_time,
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        # Prepare the report.
        report = self._prepare_report()
        print('Time elapsed (all done): {:.2f} seconds [@{}]'.format(
            time.time() - self._start_time,
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        return report, self._results

    def get_max_num_users(self):
        return max([
            v for k, v in iter(self._args.items())
            if k.endswith('_max_num_users')
        ])
