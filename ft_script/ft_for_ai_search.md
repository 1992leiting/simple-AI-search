# 写在前面
如果你已经试用了这个简单的AI搜索demo，就会发现最后一步输出总结内容对大模型的挑战较大，想要按照prompt指定的格式输出并不容易，就算是70B以上的模型也经常会出现格式不符合要求的情况。经过一定的实践，对小模型进行**LORA微调**可以达到不错的效果。

# 微调方案
其实整个AI搜索的过程，对大模型能力的要求并不高，主要还是在于最后一步的总结输出，需要按照我们想要的格式来进行；虽然体量较大的模型大概率也能满足要求，但是一般成本较高；而对小模型进行微调，可以减少成本，并且可以获得比较好的效果。
## 微调工具
我选择了modelscope的开源微调工具[swift](https://github.com/modelscope/swift)，操作简单且已经支持非常多的开源模型。

## 微调数据
由于只是对小模型的习惯进行训练，并不是要增强模型能力或者给模型投喂更多知识，所以微调数据比较简单：只需要一堆满足格式要求的问题和答案即可。数据准备过程如下：
1. 利用能力较强的大模型生成300个常识问题（我用的是claude，其他模型可能会拒绝生成这么多问题）
2. 用本项目中的网络爬取方案进行数据爬取，并保存爬取的数据
3. 基于爬取到的数据，用本项目中的总结提示词对这300个问题进行回答
    - 注意一定要使用本项目中的总结提示词，已达到更好的拟合度
    - 这一步是为了用其他能力较强的大模型生成符合要求的答案，建议使用较强的商用模型，或者70B以上的开源模型（我用的是自己搭建的qwen1.5_110B_AWQ）
    - 对于生成的答案也要做一定程度的筛选，有些问题可能并没有联网搜索到有效数据导致答案格式不满足要求，或者因为大模型回答质量较低也不是我们想要的格式（筛选越精细，最终微调的效果越好）
    - 同时这一步非常消耗tokens，注意控制推理成本
    - 不折腾的话直接用我提供的数据即可

## 微调步骤
1. 安装swift并运行微调脚本
    ```
    conda create -n swift python=3.10
    conda activate swift
    pip install 'ms-swift[all]' -U
    sh ft.sh
    ```

    - 我调用的模型是qwen2-7b-instruct，swift会自动下载原始权重；你也可以替换成其他模型
    - dataset则是指定我提供的数据
    - num_train_epochs是训练的数据遍历次数，太少的话模型输出效果可能不会提升，太大的话训练时间会比较长且容易过拟合
    - save_steps是每多少步保存一次权重
    - output_dir是保存权重的路径
2. 训练完成后，在output_dir目录下会生成微调后的权重
3. 最后记得merge权重，生成新的模型
    ```
    CUDA_VISIBLE_DEVICES=0 swift export \
        --ckpt_dir 'xxx/vx-xxx/checkpoint-xxx' --merge_lora true
    ```
更多详细的操作可以参考[swift文档](https://swift.readthedocs.io/zh-cn/latest/index.html)，我本身对微调也不是特别熟练，所以可能存在一些问题，欢迎提出。
