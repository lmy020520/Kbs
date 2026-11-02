# R2 最后一轮传统基线合同

版本 `P0B_BASELINE_CONTRACT_REPAIR_R2`，仅离线修复；不是AGGRAG新算法。父版本R1及三题真实输出冻结不变，历史状态仍为R1_SMOKE_ENGINEERING_PARTIAL。

- B0-R2：共享question-only计划 → 相同source-only证据 → Schema约束宽表。
- B1-Batch-R2：相同计划及证据 → Schema约束facts → 严格字面来源绑定 → NFKC/casefold/空白/下划线归一化 → 参数化SQL筛选及确定性宽表Join。
- Plan-R2：Schema约束query、question_units、relations、unresolved。逐字问题映射检查不等于独立语义真值，状态始终PLAN_UNVERIFIED。映射缺失/冲突/显式不确定会阻断两臂；映射通过只允许探索性执行，不能宣称计划忠实性通过。

## 相对R1的完整变化

1. 三类输出均使用显式Outlines JSON Schema约束；B0列顺序、精确行宽、外层键、facts完整字段/类型/声明谓词和Evidence ID范围受约束。没有围栏剥除、自动包裹、行填充或语义修补。
2. 新计划包增加完整原问题字符跨度、指向filter叶子/输出/主体/逻辑的JSON Pointer、所有谓词的answer_entity→value角色及未决项。旧R1计划不能自动升级。
3. 原计划核心仍是有限类型EAV表、AND/OR、eq/lt/le/gt/ge及同主体关联，程序编译参数化SQL；未增加复杂推理算法。
4. 每项来源检查新增SUBJECT_ATTRIBUTE_SUPPORT_UNVERIFIED；精确quote可以机械入库，但不会成为已核实语义事实。所有拒绝、候选总数、接受数与空结果均保留。
5. 输出Schema在CPU编译预检；生成阶段固定outlines:no-fallback，不允许静默无约束或替换解码后端。失败/截断停止，无重试。
6. Plan输出上限由1024升为2048以容纳跨度映射；两臂仍共享实际生成的同一计划。B0输出4096、Batch8192；总上下文32768，不截断原始证据。

基础模型、revision、三题顺序、原证据池、seed42、greedy、batch_size1、一张3090均不变。格式约束会改变模型生成分布，R2与R1不是同一预测配方，不能将差异称为新算法贡献。

## 公平与成本

两臂可见同样问题、计划、证据及来源信息，不访问Gold实体、表头、属性值或filter_pass。表头仅由共享计划派生。B0与Batch都受格式约束，但各自Schema不同，因此“同模型”不表示同分布/同成本。Batch额外执行来源验证、规范化、SQL及Join，全部计入墙钟和CPU成本。共享计划实际只调用一次，独立部署任一臂均须承担计划成本。

本轮调用0。未来申请最多3题、9次唯一生成（Plan3+B0 3+Batch3），每臂单独部署6次。两小时总墙钟/单次20分钟，超限停止，不重试。不得沿用旧授权。

## 可靠性边界

词面跨度/值检查既有误拒风险，也不能检测所有语义遗漏、否定、隐含关系或不恰当主体粒度。拒绝不计作正确预测；必须同时报告固定3题完成率、未验证计划、空表、非空表和候选覆盖率。不得以全部拒绝宣称安全性提升。没有自然身份或证据语义F1；只有未来真实运行后才可能报告对应官方参考下的表格指标。
