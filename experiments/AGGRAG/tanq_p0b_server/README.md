# AGGRAG P0-B Server Smoke

状态：**READY_FOR_USER_RUN只在代码成功交付GitHub后成立**。本目录本地开发完成不等于服务器运行完成。未连接GPU服务器，未在本地下载7B权重或启动推理。

唯一实验：冻结3题B0（3次）与传统B1-Batch（3次计划+3次抽取），最多9次。模型Qwen2.5-7B-Instruct-AWQ revision `b25037543e9394b818fdfca67ab2a00ecc7dd641`，单张RTX3090、总2小时、单次20分钟、无自动重试。所有题目PILOT_EXPLORATORY。

从[SERVER_SETUP.md](SERVER_SETUP.md)执行。服务器原仓库`/home/lmingyang/lmyproject/Kbs`仅用于fetch；默认新worktree保护旧KBS工作区。数据、模型、环境位于Git仓库外，运行原文/Gold/结果不公开。

- `config/`：继承原3题freeze、原提示词、Batch预注册，公开内容只有指令/ID/SHA，没有源文本或答案。
- `src/baselines.py` / `src/diagnostics.py`：原P0-B传统操作的原样副本；旧实现保持不变。GPU适配独立，未调用旧CPU-only加载器。
- `scripts/export_private_data.py`：从本地既有AGGRAG导出私有三题，确定性核对；不能输出到Git内。
- `src/preflight.py` / `src/gpu_worker.py`：固定模型/运行版本、输入校验、无Gold预测、实际GPU实现，未在本地GPU验证。
- `src/supervision.py`：外层进程组超时/清理，持久预算先占用再生成。
- `scripts/score.py`：预测SHA冻结后独立CPU官方CLI评分。scorer不被模型worker导入。
- `scripts/export_summary.py`：允许字段摘要与SHA，不导出原文/答案。
- 两份full lock包含Linux x86_64 Python3.11依赖与轮子哈希。CPU测试通过不代表AWQ内核/服务器依赖已实测兼容，失败应报告。

本次是vLLM后端及Batch粒度的独立工程适配；原prompt内容及3题/证据不变，后端和输出预算按Server配置明确记录。不是TANQ官方Oracle设置严格复现；没有新算法，没有自然独立金标性能结论。

## 上游与许可

TANQ官方评分源码commit `5c3c6c1b3b224f7f9262adbb3664bb8577d252c4`，Pix2Struct metrics commit `110d6666e8813936185fa0e9e6c38f35b387012c`。评分源文件保留作者版权头，Apache-2.0，见[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。作者数据/Wikipedia权限与代码许可分开，未将数据放入本仓库。

参考：[vLLM固定版AWQ说明](https://docs.vllm.ai/en/v0.8.5/features/quantization/auto_awq.html)、[支持硬件](https://docs.vllm.ai/en/v0.8.5/features/quantization/supported_hardware.html)、[模型官方revision](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-AWQ/tree/b25037543e9394b818fdfca67ab2a00ecc7dd641)。文档支持路径不等于本项目已在3090复现。AWQ/驱动/上下文问题不得触发静默模型或阈值替换。
