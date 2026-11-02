# R1关口决定

最终状态：**R1_GIT_DELIVERY_BLOCKED**。

本地代码与离线合同检查已完成：60项标准库测试通过，独立导出包复测通过；官方评分CLI仅UNIT_ONLY两fixture通过；旧30候选来源统计只读复现，67份原文件保护校验通过。没有R1模型响应、GPU运行、旧分数重算或30题扩展。

本地分支`aggrag-tanq-contract-r1`已提交R1实现。首次推送返回128，原因是HTTPS认证缺失（could not read Username；terminal prompts disabled），并非代码或模型失败。按照要求停止重试，不索取用户密码或Token，也不声称已上传GitHub。

负责人可在本地已认证终端执行：

```bash
git -C /home/lmy/study/Kbs_aggrag_delivery push --set-upstream origin aggrag-tanq-contract-r1
```

即使完成代码交付，也只代表可申请R1服务器Smoke，不代表已有性能改善。未来仍需新的外部R1批准文件，最多同三题9次独立生成；旧9次预算不能复用。本轮不授权运行。

R1边界：question-only计划结构可验证不等于语义正确；exact quote不等于entailment；表记规范化不等于缩写别名消歧。没有真实独立证据Gold，不计算自然F1。原SERVER_SMOKE_PARTIAL、原B0/B1输出和分数保持不变。
