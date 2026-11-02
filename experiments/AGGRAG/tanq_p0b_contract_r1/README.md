# AGGRAG P0-B Baseline Contract Repair R1

独立版本P0B_BASELINE_CONTRACT_REPAIR_R1。八份R1报告位于本目录。本轮仅CPU实现/测试/交付，GPU未授权、未执行。

使用标准库可运行：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
python scripts/verify_manifest.py
python scripts/prepare_r1.py --data-dir /path/to/private/tanq_p0b_smoke
```

输入仍为旧三题source-only，SHA、成员和顺序固定；没有数据、Gold、原始prompt响应或模型权重随代码发布。后续原生服务器环境继续使用已安装的固定推理/评分依赖，不需重下模型。`scripts/run_server_r1.py`默认在任何模型导入之前拒绝，必须有新的R1外部批准。旧9次额度不可复用。

文件结构：src/contracts.py严格JSON/计划/宽表；src/query.py参数化编译/SQLite/pivot；src/binding.py六类字面来源；src/extraction.py候选完整审计；src/pipeline.py两个新传统基线；src/r1_worker.py和r1_model.py为未来GPU适配；scripts/score_r1.py为冻结后独立评分。所有源码不按469/800/595分别硬编码逻辑。

fixtures/unit_world.json只有UNIT_ONLY合成程序测试，不能充当自然实验。旧30项历史来源计数只读复现于audit/legacy_binding_counts.json，没有旧输出修补或重新评分。

上游TANQ/Pix2Struct评分代码及Apache-2.0许可证原样保留，见THIRD_PARTY_NOTICES.md。官方RMS公式未变，精确引用不是人工Gold。R1共享question-only计划给两臂，是新配方，不能解释成原B0/B1原条件性能改善。

运行命令与安全边界见R1_SERVER_RUNBOOK.md。本轮完成后停止，等待科研验收与另行GPU授权。
