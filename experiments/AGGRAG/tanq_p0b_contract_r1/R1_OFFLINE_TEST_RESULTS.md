# R1实际离线测试

2026-11-02。本轮没有加载模型、没有新生成、没有GPU调用、没有付费API、没有重算旧自然分数。

`PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v`：60项通过。测试只需Python标准库和fixtures/unit_world.json，不需要GPU、权重或TANQ Gold。该fixture是功能测试材料，不是新研究数据或自然验证集。

覆盖：JSON对象/数组/标量/重复键；缺quote与dict型/未知ID；同页/跨页/歧义/不在源中；AND/OR与同主体多行；跨主体属性隔离和角色标签；无效模型SQL、表字段、未声明列、操作符；参数化注入字符串；数值类型与大整数；格式别名及未知语义别名不合并；行宽、长表、重复实体、null/空表；单值冲突；无候选；两臂相同输入；question-only计划；Gold元数据拒绝；新R1授权门禁。完整真实输出见audit/cpu_tests.log。

另实际使用保留的TF-CPU隔离环境运行本包未修改的官方CLI：两个UNIT_ONLY虚构fixture通过，见audit/official_fixture_check.json。这个数值只检查评分器格式行为，不是R1模型结果。标准库单元测试不依赖此可选评分环境。

旧9次响应额外只读诊断：原始Batch root均仍为list，原错误不追认成功；来源统计9/2/5/8/6复现。源与旧输出哈希未变，见audit/legacy_binding_counts.json和私有完整性回执。

未验证：R1模型是否遵循新提示、自然语义计划正确性、AWQ在R1提示长度下的真实运行、新R1的模型输出/Join成功率/官方RMS。配置继承既有运行后端不等于已经取得新成绩。后续GPU必须另批。

独立入口检查最初发现监督模块沿用旧common导入名，已在R1独立副本修正为io_utils，并增加无批准文件/否定批准模板的真实CLI回归；旧文件未修改。最终测试结果以audit/cpu_tests.log为准。
