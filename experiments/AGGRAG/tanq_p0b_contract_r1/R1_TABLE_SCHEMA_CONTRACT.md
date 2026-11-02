# R1共用宽表合同

两臂都必须输出单一对象，仅columns和rows。columns严格等于同一question-only计划生成的['entity', ...outputs.column]；不看官方参考表头，也不在评测后替换成参考名称。

每行长度必须一致，首格为非空主体字符串，一规范化主体只出现一行。重复主体、额外列、少格、嵌套值、布尔值、非有限数值、管线字符或换行单元格均TABLE_INVALID；不删行补格或自动合并模型输出。

单元格允许单行字符串、有限JSON数字、显式null。空字符串也按缺失计数，null渲染为空格后的空单元格；缺失不是已证实的负事实。空表仍必须提供完整columns与rows:[]，不能省略整个对象。

entity/attribute/value长表若不等于所需宽表列则LONG_FORM_INSTEAD_OF_WIDE。generic attribute/value不能作为计划的存储列占位符。不能通过把table包装、去围栏或改表头追认历史输出成功；根JSON类型和重复键严格检查，不做schema coercion。

官方输入仍为TANQ裸管线分隔文本：无外框、Markdown分隔行、围栏，缺失值为空。代码保留原官方RMS公式与阈值。官方首列用于实体键、后续表头参与属性匹配，因此计划属性名错误也可能扣分；这不是引入Gold表头的理由。

测试包含空表、显式缺失、重复表记别名、长宽表不一致、行宽与单元格类型，以及官方CLI的UNIT_ONLY格式检查。该检查没有使用真实TANQ标签或模型输出，不能作为论文性能。
