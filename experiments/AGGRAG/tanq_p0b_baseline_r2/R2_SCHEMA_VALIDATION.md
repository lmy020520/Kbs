# JSON Schema与约束生成

检查官方固定tag的[SamplingParams](https://github.com/vllm-project/vllm/blob/v0.8.5.post1/vllm/sampling_params.py)、[后端选择](https://github.com/vllm-project/vllm/blob/v0.8.5.post1/vllm/model_executor/guided_decoding/__init__.py)及[不支持特征检查](https://github.com/vllm-project/vllm/blob/v0.8.5.post1/vllm/model_executor/guided_decoding/utils.py)。vLLM0.8.5.post1有GuidedDecodingParams(json=...)；该版本xgrammar路径不支持minItems/maxItems等特征，故不能静默采用默认后端。

R2固定 `SamplingParams(guided_decoding=GuidedDecodingParams(json=schema,backend="outlines:no-fallback"))`。标签源码明确支持后端no-fallback选项及Outlines路径。原完整推理锁已含outlines0.1.11、outlines-core0.1.26、jsonschema4.26.0；本轮未安装vLLM/Torch或加载模型。

CPU用实际outlines-core0.1.26编译计划、表格及facts Schema为正则，测试合法与非法表示；再用jsonschema4.26.0的Draft202012Validator做独立JSON值验证。表格列使用prefixItems固定顺序和名称，rows固定minItems=maxItems为计划宽度。受控测试确认少列、多列、对象行、错列序、额外键均被拒绝；facts强制对象包、字段齐全、值类型及来源ID范围。

开发中发现旧draft tuple-items不能由该Outlines版本编译，已改用受支持prefixItems，并实际验证。这个变更只作用于新R2。任何Schema编译失败仍停止，不降级解码。

Schema不能保证答案正确、主体归属正确或条件完整。CPU正则测试不等于已验证vLLM logits处理器、实际AWQ模型输出或32K GPU运行；这些仍是下一次获批Smoke的待验项目。完整源码获取回执见audit/vllm_sources.json。
