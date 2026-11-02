# R2离线检查

84项UNIT_ONLY测试通过，日志见audit/offline_tests.log。包括继承的通用合同回归及R2新增Schema实际编译、固定行宽、额外字段、facts对象、来源范围、跨度/输出/角色/值锚点、AND/OR、参数化SQL与只读执行、实体归一化、空表/缺失值、来源错配、保留拒绝、未批准入口阻断及Gold隔离。

评分器单独在既有CPU评价环境运行2项虚构表格fixture，官方CLI退出0，预期与观察汇总一致。数值仅用于确认评分器工程链路，不是模型或TANQ开发成绩；原始回执见audit/official_fixture.json。

CPU环境Python3.12；依赖快照requirements-cpu.lock.txt（jsonschema4.26.0、outlines-core0.1.26）。未来推理仍严格要求原Python3.11与固定完整依赖；本轮没有加载vLLM、Torch、模型或GPU。没有声称已测实际CUDA约束解码。

复现（独立CPU虚拟环境）：

```bash
python -m pip install -r requirements-cpu.lock.txt
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
python scripts/verify_manifest.py
```

官方fixture需另一个按requirements-evaluation.full.lock.txt准备的评价环境：`python scripts/check_official_evaluator.py`。禁止将真实答案文件用于这些测试。
