# R1服务器执行说明：本轮只做CPU检查

用户服务器原目录`/home/lmingyang/lmyproject/Kbs`此前不是Git仓库，不能假定可fetch。本轮不改变它。若代码完成GitHub交付，可在新独立目录克隆aggrag-tanq-contract-r1；如果GitHub仍网络受限，用单独代码归档传到服务器解压，不能覆盖原AGGRAG_smoke_offline_5365154或原server_smoke结果。

## 当前允许的命令（不启动模型）

进入新代码的`experiments/AGGRAG/tanq_p0b_contract_r1`后，可直接执行：

```bash
RUNTIME=/home/lmingyang/lmyproject/aggrag_smoke_runtime
PYTHONDONTWRITEBYTECODE=1 "$RUNTIME/infer/bin/python" -m unittest discover -s tests -v
"$RUNTIME/infer/bin/python" scripts/verify_manifest.py
"$RUNTIME/infer/bin/python" scripts/prepare_r1.py --data-dir /home/lmingyang/lmyproject/aggrag_private/tanq_p0b_smoke
"$RUNTIME/eval/bin/python" scripts/check_official_evaluator.py
```

沿用既有已锁定infer/eval环境，不升级或重装；本包也保留全量依赖锁。标准库测试本身不依赖这些库，评分CLI的额外环境仅运行虚构fixture。不要把fixture分数写成TANQ成绩。

`run_server_r1.py`若没有新的批准文件，应返回GPU_NOT_AUTHORIZED，且不创建GPU进程。本轮不要把config/approval_template.json的authorized改为true。旧9次CALL_LEDGER不是R1批准文件。

## 下一轮待批准方案（不是本轮执行命令）

模型仍为Qwen2.5-7B-Instruct-AWQ、revision b25037543e9394b818fdfca67ab2a00ecc7dd641，使用服务器已有校验模型目录；不用再次下载。单张空闲3090，32K、FP16、AWQ、eager、chunked prefill2048、greedy seed42。总2小时、单次20分钟、无自动重试。不会申请8卡并行。

未来需新的Git仓库外批准JSON，authorized=true，版本/R1 CONTRACT_DIGEST摘要/三题ID及顺序/模型revision/9次上限/7200和1200秒时限完全匹配，另给唯一run_id。负责人必须先批准，再由用户创建该文件。配置文件仍保留“本轮未授权”声明，外部新批准属于下一轮，不修改冻结代码。

未来用户运行入口为 `scripts/run_server_r1.py --approval-file <新批准文件> --data-dir <原私有数据目录> --model-dir <已校验原模型目录> --gpu <单卡编号>`。本轮不提供可自动生成肯定批准的脚本，不执行该入口的授权分支。

每题顺序：共享question-only Plan→两臂同计划/同源池→B0-R1一次→B1-Batch-R1一次。计划不合法或组合payload超过1024-token保留预算则同题两臂阻断，不能另生成计划；实际context逐次计算，输入+输出+安全余量超32K直接停止，不裁剪证据。未来名义9次，计划失败可能少于9次，不能补满。

结果目录固定为新包`results/contract_r1_<run_id>/`，已存在即拒绝。加载计入总墙钟，逐次调用先记账再生成。原server_smoke文件不会读取为R1预测。

预测、calls、plans三类SHA一起冻结后，独立CPU `scripts/score_r1.py --run-dir <新结果目录> --data-dir <原私有目录>`才允许读取Gold。若三题B1未全部实际完成Join且形成可渲染宽表，评分入口阻断比较；不把失败伪装成Join完成。完成后才用原官方评分器、完整三题分母处理直接臂格式失败，不选择有利子集。

下一轮应返回：ENGINEERING_METRICS、每阶段原始响应、来源字面分类、Join状态和lineage、官方RMS（前提满足时）、全部Token和耗时。`scripts/export_summary.py`仅导出统计和SHA；原prompt、事实、quote、预测、Gold及日志保持私有，不推Git。

目前未知：R1真实格式/计划/引用/Join通过率、性能、Token和GPU耗时。不能把旧207秒或旧62,809tokens当新版本消耗，也不能因离线测试通过声称新模型表现提高。
