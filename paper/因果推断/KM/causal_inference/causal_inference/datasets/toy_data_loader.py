import os
import zipfile

import pandas as pd


def is_builtin(dataset):
    return dataset in ['lalonde']


def load_builtin(dataset):
    assert is_builtin(dataset)

    if dataset == 'lalonde':
        return load_lalonde()

    return load_lalonde()  # return lalonde by default


def load_lalonde():
    module_path = os.path.dirname(__file__)
    if os.path.exists(module_path):
        lalonde_csv_filename = os.path.join(module_path, 'data', 'lalonde.csv')
        data = pd.read_csv(lalonde_csv_filename)
    elif module_path.rfind('.zip') >= 0:
        cut_point = module_path.rfind('.zip')
        archive = zipfile.ZipFile(module_path[:cut_point + 4], 'r')
        path_in_zip = os.path.join(module_path[cut_point + 4:], 'data',
                                   'lalonde.csv')
        path_in_zip = path_in_zip.replace('\\', '/').strip('/')
        data = pd.read_csv(archive.open(path_in_zip))
    else:
        raise ValueError('Unsupported module path {}'.format(module_path))

    return data
