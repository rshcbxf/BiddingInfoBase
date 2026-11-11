# tools/archive —— 开发期一次性调试脚本（已归档，不再维护）

本目录保存的是 2026 年初排查**分项明细提取**问题时用到的临时脚本。它们已从仓库根目录移入此处，仅作为问题排查过程的记录保留，**不属于程序运行代码，也不会被 `bidding_gui` 导入**。

## 使用前提

- 所有脚本都**硬编码了作者本机路径**，直接运行前必须修改：
  - 数据库路径：`C:\Users\heqin\bidding_info.db`（程序默认库位置）
  - 个别脚本另有 `C:/DATA/Document/...` 的样例文件路径
- 脚本通过 `sys.path.insert(0, r'C:\Projects\BiddingInfoBase')` 导入项目包，换机器需同步修改。
- 建议用 Python 3.11：`py -3.11 tools/archive/check_db.py`。

## 文件清单

### 1. 数据库体检与重扫

| 文件 | 用途 |
|---|---|
| `check_db.py` | 统计 `has_itemized_list=1` 的记录、检查哪些记录“有标记但无明细”，并打印明细样例 |
| `check_details_quality.py` | 抽样检查 `itemized_details` 数据质量（设备名/品牌/型号缺省数量） |
| `check_each_file.py` | 对每条有标记的记录重新解析文件，逐条打印提取到的明细数量 |
| `debug_itemized.py` | 专查“有标记但无明细”的记录，输出文本中的分项/明细关键词匹配情况 |
| `rescan_files.py` | 重新解析库中所有文件并回写数据库（含替换明细），用于修复历史脏数据 |
| `reset_itemized.py` | **危险**：把所有 `has_itemized_list` 置 0 并清空整张 `itemized_details` 表，为全量重扫做准备 |

### 2. 单文件深度排查

针对数据库 `id=30`（射频测试设备采购项目投标文件）和 `id=2` 两个典型文件，逐步定位“空报价表模板挡住真设备明细表”的问题：

| 文件 | 用途 |
|---|---|
| `check_file_detail.py` | 重新解析 `id=2` 的文件并打印前 15 条明细 |
| `check_file_30.py` | 打印 `id=30` 文件中含“明细/清单/报价/[TABLE]”的行及上下文 |
| `check_file_30_detail.py` | 打印 `id=30` 文件完整解析结果的明细列表 |
| `check_file_30_header.py` | 查找文件中像表头的行（含数量/单位/型号/品牌） |
| `check_file_30_lines.py` | 打印第 1300–1325 行原文，查看第二个表格的真实内容 |
| `check_file_30_table.py` | 打印所有含制表符的表格行及其上下文 |
| `find_itemized_section.py` | 查找文本中“分项/明细/报价/清单”相关段落 |
| `find_table_content.py` | 只列出含 `[TABLE]` 或分项关键词的行号与内容 |
| `test_file_30_parse.py` | 模拟解析逻辑，检查第 1304 行附近能否识别表头 |
| `test_file_30_parse2.py` | 同上，检查第 485 行附近的空表头 |
| `test_full_parse.py` | 复制一份解析循环并加详细调试输出，对比正式实现 |
| `temp_test.py` | 检查目标 docx 是否存在、`is_bid_document` 为何返回 False |

### 3. 最小用例

| 文件 | 用途 |
|---|---|
| `test_itemized.py` | 用 4 段构造文本验证：有序号表、无序号表、总价表（应排除）、分项章节内表格 |

## 与当前代码的关系

- 这些脚本复制/引用了**当时的解析逻辑**，与现在的 `bidding_gui/parser.py` 可能已有差异，输出仅供参考。
- 相关结论已沉淀为根目录的 [fix_plan.md](../../fix_plan.md)（问题分析与方案）和 [fix_summary.md](../../fix_summary.md)（修复结果）。
- 如需日常运维，建议直接使用 GUI 提供的“清除无效记录”“导出 CSV”“重建数据库”，或基于 `Database` / `DocumentParser` 写新的小工具，而不是复用这些脚本。
