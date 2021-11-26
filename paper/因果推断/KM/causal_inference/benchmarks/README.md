## Benchmark 执行方式

本文档介绍如何使用 ACIC Data Challange 数据跑 Benchmark。
原始数据均位于`./data/aciccomp.tar.gz`，请自行解压到`./data/`目录下。

### 在本地跑 Benchmark

```
./benchmark.py local aciccomp 100
```

### 在 Tesla 或 YARD 跑 Benchmark

以在 Tesla 跑 Benchmark 为例介绍任务配置。请先阅读[部署](../docs/deploy.md)。

在 Tesla 中拖一个 PySpark 节点，配置如下：
1. 执行脚本：`benchmark.py`
2. 依赖包文件：`causal_inference.zip`，打包方式见[部署](../docs/deploy.md)。
3. 算法参数：`tesla aciccomp 100`（一共跑 100 份数据）
4. 资源参数：
    - `num-executors`: 丰俭由人，一个 Executor 跑一份数据
    - `driver-memory`: 1
    - `executor-cores`: 1
    - `executor-memory`: 4
    - `spark-conf` 举例（需修改 HDFS 地址）：
   ```
spark.yarn.dist.archives=hdfs://ss-wxg-3-v2/user/elsielin/causal_inference/release/causal_inference_env.zip#venv
spark.yarn.dist.files=hdfs://ss-wxg-3-v2//user/elsielin/causal_inference/datasets//aciccomp2016_covariates.csv,hdfs://ss-wxg-3-v2//user/elsielin/causal_inference/datasets//aciccomp2016_satt.csv,hdfs://ss-wxg-3-v2//user/elsielin/causal_inference/datasets//aciccomp2016_treat_outcome.csv,hdfs://ss-wxg-3-v2//user/elsielin/causal_inference/datasets//aciccomp2017_covariates.csv,hdfs://ss-wxg-3-v2//user/elsielin/causal_inference/datasets//aciccomp2017_satt.csv,hdfs://ss-wxg-3-v2//user/elsielin/causal_inference/datasets//aciccomp2017_treat_outcome.csv
spark.executorEnv.PYSPARK_PYTHON=./venv/causal_inference_env/bin/python
spark.executorEnv.R_HOME=./venv/causal_inference_env/lib/R
spark.yarn.appMasterEnv.PYSPARK_PYTHON=./venv/causal_inference_env/bin/python
spark.yarn.appMasterEnv.R_HOME=./venv/causal_inference_env/lib/R
   ```
5. 特殊参数
    - Spark 版本：tdw 3.11 - 2.2.x
    - 动态资源分配：关闭

任务执行结束后，可以在 AM 日志的`stdout`中查看各推断方法的绝对和相对误差等指标。