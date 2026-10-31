# 本地执行与未执行边界

2026-11-01。本地没有下载7B权重、没有启动任何GPU推理、没有登录服务器。

已完成：继承提示词/Batch协议/三题ID与SHA；实际导出并核验三题私有输入（原文、Gold不在Git）；CPU失败注入测试；在已有隔离TF-CPU环境真实执行本包官方评分CLI（只有UNIT_ONLY虚构fixture）；两套Linux x86_64 Python3.11依赖及哈希解析；发布载荷隔离。

`cpu_tests.log`为22项CPU测试的真实日志。`evaluator_cpu_check.json`是两个虚构表格的官方CLI行为检查，不是模型实验分数。私有输入的实际SHA校验结果只记录通过/计数，不公开问题或原文。

模型推理依赖由uv0.6.17根据固定直接版本解析到全量锁文件。初次protobuf5.29.4与vLLM依赖的opentelemetry-proto<5冲突，记录后改为独立推理环境protobuf4.25.8；评分环境保持原TF-CPU锁定依赖。完整解析已成功；**本地未安装/导入vLLM，不声称AWQ内核兼容已验证**。

从前期CPU适配切换到本服务器GPU适配：保持原提示合同、seed42、greedy和来源集合不变；显式vLLM sampling参数temperature0、top_p1、top_k=-1、repetition_penalty1、generation_config=vllm，避免模型默认生成配置隐含覆盖。原CPU-only B1实现未修改，新的后端与Batch条件分别记录，未伪称已复现原模型输出。

待用户服务器执行：模型下载/加载、SM86 AWQ兼容、32K KV与真实输入、9次生成、峰值/耗时、真实预测官方评分。未执行项没有结果，工程单元测试不能替代它们。
