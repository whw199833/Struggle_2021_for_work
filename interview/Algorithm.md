
## NLP

[Attention is all you need论文翻译](https://codle.net/attention-is-all-you-need/)

[Transformer模型的PyTorch实现_各层详解与代码解释](https://luozhouyang.github.io/transformer/)

[Attention机制_详解与代码解释](https://luozhouyang.github.io/attetnion_mechanism/)

[BERT模型详解](https://zhuanlan.zhihu.com/p/103226488)

[ELECTRA详解](https://zhuanlan.zhihu.com/p/118135466)

### 1. Bert和transformer
Bert 只有Transformer的encoder, 叠了12层, 每层有一个self attention和一个feed forward 层, 由于它只有transformer, 所以使用mask来进行训练和预测, loss函数, Mask另一个功能是让mask的部分同时接受上下游的信息进行编码训练.

Transformer 的encoder只有两层,编码能力弱, 和decoder连用后根据目标产生损失函数来更新整体的参数.

### 2. 梯度消失和梯度爆炸的解决

1. 预训练加微调
2. 梯度剪切、权重正则， L1和L2
3. 使用不同的激活函数
4. 使用batchnorm
5. 使用残差网络
6. 使用LSTM

[详解机器学习中的梯度消失、爆炸原因及其解决方法](https://blog.csdn.net/qq_25737169/article/details/78847691)

### 3. 过拟合怎么办
    增加数据
    使用更简单的模型，例如树可以使用更浅的树，权重降低
    增加regularization L1，or L2
    特征抽样
    normalization
    增加dropout
    使用不同模型进行bagging
    early stopping
