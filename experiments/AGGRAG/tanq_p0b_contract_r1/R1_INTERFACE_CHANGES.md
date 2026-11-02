# R1接口变化清单

| 项目 | 原B0 / B1-Batch | R1 |
|---|---|---|
| 版本/目录 | tanq_p0b_server，原始结果冻结 | tanq_p0b_contract_r1，独立配置、输出、调用账本 |
| 计划 | B1产生predicates+任意SQL；B0无计划 | 两臂共享question-only声明式计划，模型不再生成SQL |
| 表格schema来源 | 模型从通用entity/attribute示例自行决定 | 同一计划outputs给出required_columns；不读Gold |
| 直接臂 | 一次问题+证据生成 | B0-R1使用共同问题计划+完整证据；不再是原单次B0配方 |
| 抽取臂 | root facts对象，subject/predicate/object/evidence_id/quote | root仍必须facts对象；字段改为subject/entity_type/predicate/value/evidence_id/quote；不认列表兼容成功 |
| 类型 | set(obj)先于dict检查可能崩溃 | 先检查顶层及逐字段类型；重复JSON键、NaN、围栏均拒绝 |
| 计划执行 | 模型SQL交给SQLite | 固定facts schema，AST验证后由程序生成参数化EXISTS查询 |
| AND | 易被模型SQL写成IN并集 | 同实体每项条件单独EXISTS，再AND连接；OR独立注册 |
| 主体角色 | 单独subject_key字符串过滤容易混淆 | 只按answer entity_type聚合，同属性条件不接受subject列过滤语法；角色语义仍需观察模型 |
| 来源 | 不匹配引文没有完整分类 | exact/same-page/different-page/not-found/missing/ambiguous，严格模式只接纳exact |
| 规范化 | NFKC/casefold/空白 | 额外underscore→space；两臂同一重复键规则；不补造NYC等语义别名 |
| 输出 | ragged/围栏/长表混杂；重复未统一限制 | 同required_columns，一实体一行，NULL显式缺失，不补格不猜值 |
| 生成上限 | Plan4096/B04096/Batch8192 | shared Plan1024/B0-R14096/Batch-R18192，原生32K，计划+输出列payload额外限1024 tokens |
| 解码 | greedy | 继续greedy；不启用结构化解码，本轮没有验证其后端兼容性 |
| 冻结 | 只冻结预测 | 预测、原始calls和shared plans同时冻结，之后才允许评分 |
| 评分前提 | B1未Join也出现0分 | 三题B1均实际完成Join且有合法宽表才允许任务效果评分；否则只报工程状态 |

B1-R1使用来源字段且执行引用校验，B0-R1只有直接表格，不伪造B0引用通过率。两臂格式约束和公开证据相同，但不是仅开关Join的单变量消融。

主体别名边界：支持NFKC、大小写、空白和下划线表记变体；不自动合并缩写、不同语言名、去括号后重名或同名异实体。原输入没有独立可见别名登记，因此不提供Gold别名映射。测试也明确验证未知别名不会被猜测合并。该限制不能被“规范化测试通过”掩盖。
