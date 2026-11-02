# R1结构化计划与SQL合同

## 计划

模型只能输出一个JSON对象，精确字段：version=r1、entity_type、predicates、outputs、filter。predicates每项为name/kind(text或number)/cardinality(one或many)；outputs每项为predicate/column，必须引用声明predicate，column与该公开predicate的规范化名称一致，至少一个属性。first column统一entity，不能只输出subject一列。

filter为逻辑组{op:and或or,conditions:[...]}或叶子{predicate,operator,value}。文本只支持eq，数值支持eq/lt/le/gt/ge且必须cardinality=one。只接受有限数值，整数绝对值不超过2^53，避免隐式精度损失。空and表示无过滤，空or非法；最多16谓词、12输出、每组16子项、深度4、总64节点。这些是固定可执行子集，不是用开发分数调出的阈值。NOT/开放世界否定/跨实体任意关系查询不支持则PLAN_INVALID，不自拟近似计划。

不接受sql、table、任意column名或数据库列名充当semantic predicate。语义属性如owner是一项关系，人名是该属性的value；模型不能指定subject_key等SQL列过滤。程序验证结构和内部角色/类型一致，不声称能独立证明entity_type或AND/OR解析与自然问题语义相符。

## 编译

只使用程序创建的facts表，列为subject_key、subject、entity_type_key、predicate_key、object、object_key、numeric_value、evidence_id、raw_index。predicate/value/type一律为绑定参数，SQL标识符完全由程序决定。SQL生成器只产生SELECT DISTINCT/EXISTS/AND/OR/固定比较符，不执行模型SQL或自动把relation_facts改名。

AND针对同一subject_key和entity_type_key的每项约束生成独立EXISTS，允许不同fact行共同满足条件。OR才是任选一项。不会把AND写为IN列表。按NFKC/casefold/underscore/空白键合并主体，保留首个显示名；这只是表记规范化，不是同名实体消歧。

## 执行与pivot

内存SQLite仅加载严格通过的候选，authorizer仅允许SELECT和读取facts；禁用其他关系、写操作和SQL函数，设VM步数及10,000行上限。numeric_value仅接纳已通过number合同的JSON数字，不把“13 episodes”强转13。

选中主体后按计划属性pivot。many属性对相同规范化值去重、稳定排序后以逗号连接，保留全部来源lineage；不切分原始逗号字符串来猜实体。one属性出现不同值时记录SINGLE_VALUE_CONFLICT，不凭条件挑有利数值，相关主体保留在冲突记录、不产生已确认行，状态JOIN_PARTIAL。缺少输出属性时填显式null，并保留missing信息；这是“未抽取到值”，不是事实不存在。

没有满足条件的抽取主体时可合法输出空表；not_selected_entity_keys保留排除轨迹，含义是未在抽取事实中匹配，不代表全世界不存在。SQL完成、宽表完成、来源定位、条件语义是不同的判定，不能互相替代。
