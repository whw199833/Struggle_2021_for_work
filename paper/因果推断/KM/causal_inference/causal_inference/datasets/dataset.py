import sys

import pandas as pd
from pandas.api.types import is_numeric_dtype
from pandas.util import hash_pandas_object
from rpy2.robjects import FloatVector, pandas2ri
from rpy2.robjects.packages import importr

from causal_inference.datasets.toy_data_loader import is_builtin, load_builtin
from causal_inference.estimators.utils import is_binary
from causal_inference.utils.config_parser import Converters

pandas2ri.activate()


class Dataset:
    default_config = dict({
        'dataset_filter': '',
        'categorical_covariates': '',
        'max_num_users': sys.maxsize
    })
    converter_rules = dict({
        'dataset': str,
        'dataset_filter': str,
        'covariates': Converters.string_list_converter,
        'categorical_covariates': Converters.string_list_converter,
        'treat': str,
        'outcomes': Converters.string_list_converter,
        'max_num_users': int
    })
    converter_rules_tdw = dict({'tdw_username': str, 'tdw_password': str})

    def __init__(self,
                 data,
                 covariates,
                 treat,
                 outcomes,
                 categorical_covariates=None,
                 propensity=None,
                 sort=False):
        # Preprocess arguments.
        if categorical_covariates is None:
            categorical_covariates = []

        # Check whether covariates / treat / outcomes are valid.
        all_variables = list(list(covariates) + list([treat]) + list(outcomes))
        assert len(set(all_variables)) == len(
            all_variables), 'Duplicated covariate/treat/outcome'
        for v in all_variables:
            assert v in data.columns.values, '{} is not in the data.'.format(v)
            assert v in categorical_covariates or is_numeric_dtype(
                data[v]), '{} is not numeric.'.format(v)
        for v in categorical_covariates:
            assert v in data.columns.values, '{} is not a covariate.'.format(v)

        # Check the treat column.
        assert is_binary(data[treat]), 'Treatment indicator should be 0 or 1.'
        assert data[data[treat] == 1].shape[0] > 0, 'No treated unit.'
        assert data[data[treat] == 0].shape[0] > 1, 'No control unit.'

        # Check the propensity score.
        if propensity is not None:
            assert len(propensity) == data.shape[0]

        # Initialize other variables.
        self.data = data[all_variables].fillna(0.0).reset_index(drop=True)
        self.propensity = propensity
        self.covariates = covariates
        self.treat = treat
        self.outcomes = outcomes
        self.size = self.data.shape[0]

        # One-hot encoding.
        if categorical_covariates:
            # Get one-hot encoding.
            self.data = pd.get_dummies(self.data,
                                       columns=categorical_covariates,
                                       dtype=int)

            # Update covariates.
            self.covariates = sorted(
                list(set(self.data.columns.values) - {treat} - set(outcomes)))

        # Sort.
        if sort:
            self.sort_in_place()

    @classmethod
    def from_local_file(cls, config, propensity=None, sort=True):
        if is_builtin(config['dataset']):
            data = load_builtin(config['dataset'])
        else:
            data = pd.read_csv(config['dataset'])
            if config['dataset_filter']:
                data = data.query(config['dataset_filter'])
        sample_size = min(data.shape[0], config['max_num_users'])
        data = data.sample(n=sample_size, random_state=42)
        return cls(data,
                   config['covariates'],
                   config['treat'],
                   config['outcomes'],
                   categorical_covariates=config.get('categorical_covariates'),
                   propensity=propensity,
                   sort=sort)

    @classmethod
    def from_tdw_table(cls, spark, config, propensity=None, sort=True):
        if is_builtin(config['dataset']):
            data = load_builtin(config['dataset'])
        else:
            from pytoolkit3 import TDWSQLProvider

            if config['dataset'].find(';') >= 0 \
                    or config['dataset_filter'].find(';') >= 0:
                raise ValueError('Find ; in dataset or dataset_filter')
            tdw_db, tdw_table = config['dataset'].strip().split('::')
            user = config.get('tdw_username')
            user = None if not user else user
            password = config.get('tdw_password')
            password = None if not password else password
            tdw = TDWSQLProvider(spark, user=user, passwd=password, db=tdw_db)
            df = tdw.table(tdw_table)
            if config['dataset_filter']:
                df = df.filter(config['dataset_filter'])
            df.cache()
            df_size = df.count()
            df = df.sample(False,
                           fraction=min(
                               1.0, 1.1 * config['max_num_users'] / df_size))
            data = df.toPandas()
        sample_size = min(data.shape[0], config['max_num_users'])
        data = data.sample(n=sample_size, random_state=42)

        return cls(data,
                   config['covariates'],
                   config['treat'],
                   config['outcomes'],
                   categorical_covariates=config.get('categorical_covariates'),
                   propensity=propensity,
                   sort=sort)

    def sort_in_place(self):
        # Sort columns.
        self.data = self.data.reindex(sorted(self.data.columns), axis=1)
        # Sort rows.
        h = hash_pandas_object(self.data, index=False)
        h.sort_values(inplace=True)
        self.data = self.data.reindex(h.index)
        self.data.reset_index(drop=True, inplace=True)
        if self.propensity is not None:
            self.propensity = self.propensity[h.index]

    def has_propensity_score(self):
        return self.propensity is not None

    def add_propensity_score(self, propensity):
        assert len(propensity) == self.data.shape[0]
        self.propensity = propensity

    def get_propensity_score(self):
        return self.propensity

    def get_treatment(self):
        return self.data[self.treat]

    def get_covariates(self, add_pscore=False):
        if add_pscore:
            assert self.has_propensity_score()
            return pd.concat(
                [self.data[self.covariates],
                 pd.Series(self.propensity)],
                axis=1)
        return self.data[self.covariates]

    def get_outcome(self, outcome):
        return self.data[outcome]

    def set_outcome(self, outcome, v):
        self.data[outcome] = v

    def get_r_dataframe(self):
        data_r_df = pandas2ri.py2ri(self.data[[self.treat] + self.covariates +
                                              self.outcomes])
        return data_r_df

    def get_ri_covariates(self):
        covariates_r_df = pandas2ri.py2ri(self.data[self.covariates])
        return covariates_r_df

    def get_ri_treatment(self):
        treat_r_df = FloatVector(self.data[self.treat].values)
        return treat_r_df

    def get_ri_outcome(self, outcome):
        outcome_r_df = FloatVector(self.data[outcome].values)
        return outcome_r_df

    def get_ri_propensity_score(self):
        assert self.has_propensity_score()
        ps_r_pf = FloatVector(self.propensity)
        return ps_r_pf

    def get_ri_treatment_formula(self):
        stats = importr("stats")
        pscore_fml = stats.formula(self.treat + "~" +
                                   "+".join(self.covariates))
        return pscore_fml

    def get_ri_outcome_formula(self, outcome_name, add_covariates=True):
        stats = importr("stats")
        if add_covariates:
            fml = stats.formula(outcome_name + "~" + self.treat + "+" +
                                "+".join(self.covariates))
        else:
            fml = stats.formula(outcome_name + "~" + self.treat)
        return fml

    def sample(self, max_num_users, outcome_name=None, random_state=42):
        if self.size > max_num_users:
            idx = self.data.sample(n=max_num_users,
                                   random_state=random_state).index
        else:
            idx = self.data.index
        data = self.data.loc[idx, :]
        propensity = self.propensity[
            idx] if self.propensity is not None else None
        outcomes = [outcome_name
                    ] if outcome_name is not None else self.outcomes
        return Dataset(data,
                       self.covariates,
                       self.treat,
                       outcomes,
                       propensity=propensity,
                       sort=True)

    def subset(self, idx, keep_propensity):
        data = self.data.loc[idx, :]
        if keep_propensity and self.propensity is not None:
            propensity = self.propensity[idx]
        else:
            propensity = None
        return Dataset(data, self.covariates, self.treat, self.outcomes,
                       propensity)
