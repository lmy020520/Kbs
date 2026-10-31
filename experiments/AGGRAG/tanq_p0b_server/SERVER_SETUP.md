# P0-B Server Smoke：用户执行说明

本轮只有固定三题B0+传统B1-Batch，**最多9次生成**。不用8卡并行，不跑30题，不跑逐单元B1，不调用付费API。数据、完整prompt、Gold及运行结果均不得推送GitHub。

## 1. 安全获取分支，保留原KBS工作区

服务器原仓库是 `/home/lmingyang/lmyproject/Kbs`。先确认origin确实指向指定Kbs仓库。无论原目录是否有本地改动，推荐独立worktree；不切换或覆盖原KBS工作区，不运行reset/clean/stash。

```bash
cd /home/lmingyang/lmyproject/Kbs
git status --short
git remote get-url origin
# 确认输出是 https://github.com/lmy020520/Kbs.git 或同仓库SSH地址后再继续。
git fetch origin refs/heads/aggrag-p0b-server-smoke:refs/remotes/origin/aggrag-p0b-server-smoke
# 下列目标必须尚不存在；若存在，先检查，不删除或覆盖。
git worktree add --detach /home/lmingyang/lmyproject/Kbs_AGGRAG_smoke origin/aggrag-p0b-server-smoke
cd /home/lmingyang/lmyproject/Kbs_AGGRAG_smoke/experiments/AGGRAG/tanq_p0b_server
git rev-parse HEAD
python3 scripts/verify_public_manifest.py
```

目标GitHub远程在本次查询中没有已有分支；因此本次分支只包含独立实验目录，不能用它覆盖服务器可能已存在的原KBS文件。worktree是为此设置的安全默认方案。若服务器不是有效Git工作树或origin不对应，停下核查，不git init覆盖旧项目。

## 2. 环境及单卡选择

锁文件目标为Linux x86_64、Python3.11、manylinux_2_28及兼容更高glibc。模型元数据约5.57GB；推理轮子/依赖另占大量磁盘，建议环境+缓存预留至少30GB，主存32GB，单张24GB RTX3090。实际兼容性以本次加载为准。

```bash
nvidia-smi
free -h
df -h .
python3.11 --version
# 人工确认一张空闲3090，改成实际GPU编号；不自动选择或清理别人的GPU任务。
export CUDA_VISIBLE_DEVICES=0
export AGGRAG_GPU=0
export AGGRAG_HOME=/home/lmingyang/lmyproject/aggrag_smoke_runtime
export AGGRAG_DATA=/home/lmingyang/lmyproject/aggrag_private/tanq_p0b_smoke
export AGGRAG_MODEL=/home/lmingyang/lmyproject/aggrag_models/Qwen2.5-7B-Instruct-AWQ-b2503754
mkdir -p "$AGGRAG_HOME"
python3.11 -m venv "$AGGRAG_HOME/infer"
python3.11 -m venv "$AGGRAG_HOME/eval"
"$AGGRAG_HOME/infer/bin/python" -m pip install --require-hashes -r requirements-inference.full.lock.txt
"$AGGRAG_HOME/eval/bin/python" -m pip install --require-hashes -r requirements-evaluation.full.lock.txt
"$AGGRAG_HOME/infer/bin/python" -m pip check
"$AGGRAG_HOME/eval/bin/python" -m pip check
"$AGGRAG_HOME/infer/bin/python" -m pip freeze > "$AGGRAG_HOME/infer-installed.txt"
"$AGGRAG_HOME/eval/bin/python" -m pip freeze > "$AGGRAG_HOME/eval-installed.txt"
"$AGGRAG_HOME/infer/bin/python" scripts/server_environment.py > "$AGGRAG_HOME/server_environment.json"
PYTHONDONTWRITEBYTECODE=1 python3.11 -m unittest discover -s tests -v
"$AGGRAG_HOME/eval/bin/python" scripts/check_evaluator.py
```

若安装或pip check失败，保留完整日志并停止。不能自行更换vLLM/torch/量化版本以“跑通”。OpenAI SDK仅是vLLM依赖，代码没有付费API路径。官方评分在单独CPU TensorFlow环境，避免其protobuf约束与推理冲突。

## 3. 私有数据准备与传输（不走公开Git）

本地已导出并核对的目录：`/home/lmy/study/AGGRAG/experiments/tanq_server_smoke_private_transfer/`。包含三题inputs和隔离evaluation参考。沿用既有TANQ/Wikipedia许可边界，只供获准私人研究使用；没有赋予公开再发布权。

若需要重新导出，在本地代码目录运行（目标必须未存在且在Git仓库外）：

```bash
python3 scripts/export_private_data.py \
  --aggrag-root /home/lmy/study/AGGRAG \
  --out /home/lmy/study/AGGRAG/experiments/tanq_server_smoke_private_transfer_new
```

用户通过已有SSH/SFTP连接把该私有目录内容传到服务器 `$AGGRAG_DATA/`，保持目录结构：

```text
$AGGRAG_DATA/
  inputs/source_only.jsonl
  evaluation/reference.jsonl
  PRIVATE_TRANSFER_RECEIPT.json
```

例如在本地使用自己已有的SSH别名，**自行替换`YOUR_SERVER_ALIAS`**（不在命令中填写密码/Token）：

```bash
ssh YOUR_SERVER_ALIAS 'umask 077; mkdir -p /home/lmingyang/lmyproject/aggrag_private/tanq_p0b_smoke'
scp -r /home/lmy/study/AGGRAG/experiments/tanq_server_smoke_private_transfer/. \
  YOUR_SERVER_ALIAS:/home/lmingyang/lmyproject/aggrag_private/tanq_p0b_smoke/
```

该传输由用户执行，Codex没有登录服务器。若许可/账号访问不允许私人传输，停止为SERVER_DATA_BLOCKED，不上传到Git替代。`config/private_data_manifest.json`只有ID与SHA；输入不符即停止，不能拿别的数据替代。

## 4. 下载已批准的官方固定模型

仅在GPU服务器运行此步骤；不在本地4060下载。

```bash
"$AGGRAG_HOME/infer/bin/python" scripts/download_model.py \
  --model-dir "$AGGRAG_MODEL" --authorized-server-download
```

脚本先通过官方HF API确认repo及revision，再下载固定snapshot，核对LFS SHA并逐文件计算SHA，写`AGGRAG_MODEL_RECEIPT.json`。不下载/执行远程Python代码。已有非空目录不会被混入覆盖；不要手工改receipt以跳过校验。

## 5. CPU数据/上下文预检查

```bash
"$AGGRAG_HOME/infer/bin/python" scripts/preflight.py \
  --data-dir "$AGGRAG_DATA" --model-dir "$AGGRAG_MODEL" \
  > "$AGGRAG_HOME/preflight.json"
```

核对固定三题及证据顺序、SHA、模型文件SHA、AWQ/native32K配置、实际7B tokenizer长度、依赖版本。32K限制是**输入+最大输出**；Batch还保留predicate和安全余量。不能拿旧1.5B tokenizer估计替代本次7B核验。失败即停，不截断/换题/换模型。

## 6. 一次GPU预加载、32K容量检查及9次真实Smoke

为把加载计入2小时，预加载和生成统一在一个受监督进程中完成，**不另跑一次无限时的GPU加载测试**。结果目录必须从未存在。不要删除已存在目录重试。

```bash
export AGGRAG_RUN="$PWD/results/server_smoke"
"$AGGRAG_HOME/infer/bin/python" scripts/run_server.py \
  --data-dir "$AGGRAG_DATA" --model-dir "$AGGRAG_MODEL" \
  --out "$AGGRAG_RUN" --gpu "$AGGRAG_GPU"
```

只有一张可见RTX3090，tensor_parallel_size=1、max_num_seqs=1、seed42、greedy（temperature0/top_p1/top_k=-1/repetition_penalty1，generation_config=vllm）、FP16、AWQ、eager，chunked prefill2048减少prefill激活峰值，不改变原文。要求所选GPU空闲至少22000MiB，资源不足不会自动换卡。

模型初始化后记录实际engine max_model_len和KV容量，均须支持32768；然后用实际问题验证长度。不会额外生成合成32K探针以突破9次调用：所验证的是配置/KV容量及真实请求，不能称为实测生成了完整32768 token。

每次生成前先持久化预算；总墙钟7200秒（含加载）、单次生成1200秒；超时终止本任务进程组，不杀其他任务、不自动续写/重试。OOM、输出达到length上限、上下文不足则停。格式不合格明确记录，计划格式失败可导致不足9次，不能用模拟响应补齐。若命令非零退出，先看私有日志，不立刻重跑。

## 7. 冻结后评分、报告与SHA

GPU进程结束后自动冻结预测SHA；评分是独立CPU进程，才打开evaluation参考：

```bash
# 确认有PREDICTIONS_FROZEN.json；若GPU运行前数据就阻塞，不评分。
"$AGGRAG_HOME/eval/bin/python" scripts/score.py \
  --run-dir "$AGGRAG_RUN" --data-dir "$AGGRAG_DATA"
"$AGGRAG_HOME/infer/bin/python" scripts/hash_results.py --run-dir "$AGGRAG_RUN"
cat "$AGGRAG_RUN/SMOKE_GATE_DECISION.md"
```

官方RMS原样保留；未执行案例不伪造成空预测。部分运行的评分分母明确列出，不作三题完整成绩。9次返回、格式/quote/Join正常、两臂三题都完成评分才会SERVER_SMOKE_SUCCESS。低分本身不是工程失败，高分也不证明新算法价值。未完成人工语义审核，不计算自然F1。

## 8. 只导出脱敏摘要供审核

```bash
"$AGGRAG_HOME/infer/bin/python" scripts/export_summary.py \
  --run-dir "$AGGRAG_RUN" --out "$AGGRAG_HOME/share_summary"
```

仅导出允许字段的状态/Token/模型/官方汇总分数及私有文件SHA，不含问题、表格、答案、quote、prompt或原始响应。人工检查`share_summary`后返回给负责人；可另通过私有渠道提供原始结果。**不要git add results、私有数据、模型或日志；不自动push任何结果。** 此轮结束，不能自行扩为30题。
