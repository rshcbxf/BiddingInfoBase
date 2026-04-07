# 总结问题修复

## 问题描述
部分分项明细为"是"的记录在查看详情时弹出的窗体不显示分项明细。

## 问题根源

1. **`has_itemized_list` 标记与实际明细数据不一致**
   - `_check_itemized_list()` 只检测文本中是否包含"分项"、"明细"等关键词
   - `_extract_itemized_details()` 提取表格数据时需要满足更严格的条件
   - 导致有些文档被标记为 `has_itemized_list=True`，但实际提取不到明细数据

2. **表格提取逻辑过于宽松**
   - 只要表头匹配 3 个以上列名就开始提取
   - 没有验证提取的数据是否是真正的设备明细
   - 把签字栏、备注表、评审标准表等非设备表格也提取出来

3. **空表格问题**
   - 有些文档包含空的报价表模板（只有表头，数据行为空）
   - 提取器把这些空表格当成设备明细表

## 已完成的修复

### 修复 1: 统一 `has_itemized_list` 判断逻辑
```python
# 修改前
result.has_itemized_list = self._check_itemized_list(text)
if result.has_itemized_list:
    result.itemized_details = self._extract_itemized_details(text)

# 修改后
result.itemized_details = self._extract_itemized_details(text)
result.has_itemized_list = len(result.itemized_details) > 0
```

### 修复 2: 加强表头验证
```python
# 必须包含设备名称列 + 数量/单位列
has_device_name = 'device_name' in header_indices
has_quantity = bool(header_indices.keys() & required_quantity_columns)

if has_device_name and has_quantity:
    in_itemized_table = True
    has_valid_table = True
```

### 修复 3: 过滤无效设备名称
```python
invalid_device_keywords = ['签字', '盖章', '备注', '税率', '投标', '招标', '公司',
                           '序号', '项目名称', '项目编号', '投标总报价', '交货时间']

if detail.device_name:
    if len(detail.device_name.strip()) <= 2:
        is_valid_device = False
    for kw in invalid_device_keywords:
        if kw in detail.device_name:
            is_valid_device = False
            break
```

### 修复 4: 跳过空表格
```python
# 如果连续处理了很多行但没有提取到有效数据，重置表格状态
if in_itemized_table and consecutive_data_rows == 0 and header_indices:
    if len(details) == 0 and i > 100:
        in_itemized_table = False
        header_indices = {}
```

### 修复 5: 移除"序号"列的强制要求
之前要求表格必须包含"序号"列才是设备明细表，这导致一些没有序号列的表格被排除。
现在只要求包含"设备名称"和"数量/单位"列即可。

## 测试结果

修复前:
- 26 条记录标记为 `has_itemized_list=1`
- 只有 10 条记录有实际明细数据
- 16 条记录有标记但无数据

修复后:
- 8 条记录标记为 `has_itemized_list=1`
- 8 条记录都有实际明细数据
- 有标记但无数据的记录数：0

## 后续优化建议

1. 增加对 PDF 表格的解析能力（当前对某些 PDF 文件解析效果不佳）
2. 改进表格结构识别，更好地区分设备明细表和其他表格
3. 增加对表格数据完整性的验证
