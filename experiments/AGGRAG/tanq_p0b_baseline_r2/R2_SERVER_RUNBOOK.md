# R2服务器准备及资源申请（未批准执行）

当前仅CPU离线修复获授权。不得运行GPU。未来运行需负责人另行明确批准并提供匹配当前CONTRACT_DIGEST、版本、模型、三个固定sample ID及唯一run_id的authorized=true文件。config/approval_template.json保持false；旧R1授权不匹配。

服务器仓库 `/home/lmingyang/lmyproject/Kbs`，建议独立worktree，代码分支aggrag-tanq-baseline-r2，目录experiments/AGGRAG/tanq_p0b_baseline_r2。获取前先git status，存在改动时保留，不reset/clean；不覆盖原仓库。数据与权重仍使用服务器既有私有目录，不公开上传，不重新下载。

CPU验收命令（进入R2目录，使用含CPU锁依赖的环境）：

```bash
python scripts/verify_manifest.py
python -m unittest discover -s tests -v
python scripts/prepare_r2.py --data-dir /home/lmingyang/lmyproject/aggrag_private/tanq_p0b_smoke
```

## 仅申请、未批准的GPU范围

- 原已消费开发3题，原固定Qwen2.5-7B-Instruct-AWQ revision b25037543e9394b818fdfca67ab2a00ecc7dd641。
- 一张空闲RTX3090，32K上下文，seed42/greedy/batch1；不得减上下文或截证据。
- 最多9次唯一生成：3共享Plan、3B0、3Batch；每臂独立成本6次。计划被拒绝则实际调用更少，分母保持固定3，不补题/补调用。
- 总墙钟7200秒、单次1200秒，无自动重试。Schema/模型不兼容立即保留错误停止，不切后端。
- 记录Schema及编译秒数、提示/响应/usage、plan trace与UNVERIFIED、来源检查、Join、空表、环境及SHA。实际logits编译开销包含于generate秒数，CPU正则预检单列，不漏计。

## 获批后才可用的入口

`python scripts/run_server_r2.py --approval-file <新的R2授权JSON> --data-dir <私有数据根> --model-dir <既有固定AWQ目录> --gpu <明确单卡号>`

未经授权入口退出GPU_NOT_AUTHORIZED，不加载模型。每次run独立目录；存在则停止，不覆盖旧结果。结果冻结后才允许独立CPU评分入口读取reference；3题B1未全部完成Join则不比较效果。

报告必须区分格式率、词面计划追溯率、未验证计划、候选机械绑定率、非空/空Join及官方参考下表格指标。不能把纯格式通过算作语义验证。R2仍需逐题审阅残余问题，成功也不授权30题或新算法。
