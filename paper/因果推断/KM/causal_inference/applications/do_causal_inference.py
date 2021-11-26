import argparse
import warnings

from causal_inference import CausalEstimatorWrapper
from causal_inference.datasets import Dataset
from causal_inference.utils.config_parser import create_dict_from_ini_file
from causal_inference.utils.config_parser import create_dict_from_argv


def parse_config(args, config_filename=None, config_argv=None):
    default_config = {
        **CausalEstimatorWrapper.default_config,
        **Dataset.default_config, 'output_filename': ''
    }
    converter_rules = {
        **CausalEstimatorWrapper.converter_rules,
        **Dataset.converter_rules, 'output_filename': str
    }
    if args.mode == 'yard':
        converter_rules['tdw_username'] = str
        converter_rules['tdw_password'] = str

    # Parse configs.
    if config_filename:
        config = create_dict_from_ini_file(config_filename, converter_rules,
                                           default_config)
    else:
        config = create_dict_from_argv(config_argv, converter_rules,
                                       default_config)

    # Special settings for debugging.
    if args.mode == 'yard_debug':
        config['dataset'] = 'lalonde'

    return config


def main_local(args, config_filename, config_argv):
    # Parse all configs.
    config = parse_config(args, config_filename, config_argv)

    # Test the output file before doing anything.
    if config['output_filename']:
        with open(config['output_filename'], 'w+') as f:
            f.write('Causal Inference Report')

    # Causal inference.
    ci = CausalEstimatorWrapper(config)
    config['max_num_users'] = min(config['max_num_users'],
                                  ci.get_max_num_users())
    dataset = Dataset.from_local_file(config, sort=True)
    causal_inference_results, _ = ci.inference(dataset)

    # Print results to log.
    print('-------------------------------------------------------------')
    print('Causal inference logs')
    print('-------------------------------------------------------------')
    print(causal_inference_results)

    # Write results.
    if config['output_filename']:
        with open(config['output_filename'], 'w+') as f:
            f.write(causal_inference_results)

    return causal_inference_results


def main_spark(args, config_filename, config_argv):
    from pyspark import SparkFiles
    from pyspark.sql import SparkSession
    from pyspark.sql.types import StringType

    spark = SparkSession.builder.appName('Causal Inference').getOrCreate()
    sc = spark.sparkContext

    if config_filename and args.mode in ('yard', 'tesla'):
        sc.addFile(config_filename)
        config_filename = SparkFiles.get(config_filename)

    # Parse configs.
    config = parse_config(args, config_filename, config_argv)

    # Causal inference.
    ci = CausalEstimatorWrapper(config)
    config['max_num_users'] = min(config['max_num_users'],
                                  ci.get_max_num_users())
    dataset = Dataset.from_tdw_table(spark, config, sort=True)
    causal_inference_results, _ = ci.inference(dataset, spark_context=sc)

    # Print results to log.
    print('-------------------------------------------------------------')
    print('Causal inference logs')
    print('-------------------------------------------------------------')
    print(causal_inference_results)

    # Output the results.
    if config['output_filename']:
        df = spark.createDataFrame([causal_inference_results], StringType())
        df.coalesce(1).write.format('text').option(
            'header',
            'false').mode('overwrite').save(config['output_filename'])

    return causal_inference_results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode',
                        help='where to run',
                        choices=['local', 'yard', 'tesla', 'yard_debug'],
                        type=str)
    parser.add_argument('config',
                        help='how to specify configurations',
                        choices=['file', 'argv'],
                        type=str)
    parser.add_argument('--config_filename',
                        help='*.ini',
                        type=str,
                        default='')

    args, config_argv = parser.parse_known_args()

    if args.config == 'file':
        config_filename = args.config_filename
        config_argv = None
        if not config_filename:
            raise ValueError('--config_filename not set')
    else:
        config_filename = None

    if args.mode == 'local':
        return main_local(args, config_filename, config_argv)

    if args.mode in ('yard', 'tesla', 'yard_debug'):
        return main_spark(args, config_filename, config_argv)

    raise ValueError('Unknown mode: {}'.format(args.mode))


if __name__ == "__main__":
    warnings.filterwarnings(module='sklearn*',
                            action='ignore',
                            category=DeprecationWarning)

    main()
