# R1来源绑定与历史冻结回执

旧原始30候选的字面检查实际只读复现：

| 状态 | 数量 | 严格模式 |
|---|---:|---|
| EXACT_SOURCE_MATCH | 9 | 只表明quote在声明源中连续原样存在，可作为机械绑定输入 |
| SAME_PAGE_OTHER_CHUNK | 2 | 拒绝，不自动改Evidence ID |
| DIFFERENT_PAGE_MATCH | 5 | 拒绝，保留其他页面匹配候选 |
| QUOTE_NOT_FOUND | 8 | 拒绝，不推断事实为假 |
| MISSING_QUOTE | 6 | 拒绝，不填补quote |
| AMBIGUOUS_SOURCE | 0 | 拒绝，保留全部可能来源 |

这是24项带quote、6项缺失的原历史统计，保持不变。脚本只将旧root列表逐项作为forensic候选检查，不包装成facts、不认作R1通过、不重新评分。audit/legacy_binding_counts.json是本次实际执行回执，私有原始响应未加入Git。

严格解析先验Evidence ID字符串与集合成员，再逐字段检查事实，missing/null/错误类型不被补为合法值。unknown或错误类型ID另列INVALID_EVIDENCE_ID；缺quote列MISSING_QUOTE。每项原始失败输入和原因都保留，未悄悄删除。字段schema通过也不能替代quote来源检查。

字面坐标以JSON Pointer+Python Unicode字符起止表示。大小写、空白、标点不作模糊修复。HTTP/HTTPS统一页面身份，URL片段忽略，query/revision保留；Wikipedia路径仅做百分号/NFKC及下划线表记处理，不猜不同页面同一实体。

若声明源中确有quote，状态EXACT_SOURCE_MATCH，即使别处也出现同文，也不擅自改源；多处字符坐标单列multiple_spans。若声明源不匹配且另有多个可能源，状态AMBIGUOUS_SOURCE。只有一个其他匹配时才分同页/跨页。无法确定页面身份也保留AMBIGUOUS_SOURCE。以上均为机械定位，不是语义正确率、人工Gold或完整证据充分性证明。

没有开发来源图谱、模糊重绑定或新归因算法。source-only固定池与B0完全相同，不读取Gold实体映射或filter_pass。
