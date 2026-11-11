# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

投标文件信息管理系统 - 跨平台 GUI 程序，用于扫描、解析和管理投标文件信息。对外文档见 [README.md](README.md)。

## 运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 运行程序
python -m bidding_gui.main
# 或
python bidding_gui/main.py

# 指定数据库（优先级：--db > 环境变量 BIDDING_DB_PATH > 用户主目录 bidding_info.db）
python -m bidding_gui.main --db D:\data\bidding.db
```

## 项目结构

```
C:\Projects\BiddingInfoBase\
├── bidding_gui/
│   ├── __init__.py         # 包初始化，导出公共接口、版本号
│   ├── main.py             # 程序入口
│   ├── app.py              # GUI 主窗口（customtkinter）
│   ├── database.py         # SQLite 数据库操作
│   ├── parser.py           # 文档解析器（PDF/DOC/DOCX）
│   └── scanner.py          # 文件扫描器（支持中断、增量扫描）
├── tools/archive/          # 开发期一次性调试脚本（已归档，不参与运行、不要复用）
├── tests/                  # pytest 回归用例
├── sample_doc/             # 本地测试语料（真实文档，已 gitignore）
├── requirements.txt
├── requirements-dev.txt    # 开发依赖（含 pytest）
├── pytest.ini
├── README.md               # 对外使用说明
├── CLAUDE.md
├── fix_plan.md / fix_summary.md   # 分项明细问题的分析与修复记录
└── .gitignore
```

## 核心模块说明

### database.py
- `Database` 类：SQLite 数据库操作；`BiddingProject`、`ItemizedDetail` 数据模型。
- 连接建立时执行 `PRAGMA foreign_keys = ON`，使 `itemized_details` 的 `ON DELETE CASCADE` 生效；`delete_by_id/delete_by_ids` 另有显式删除明细的兜底。
- 打开数据库时 `_cleanup_orphan_details()` 清理历史遗留的孤儿明细（`project_id` 不存在的明细行）。
- `_migrate()` 兼容旧库：把旧的 `bid_content` 字段迁移为 `has_itemized_list`（建新表→搬数据→改名）。
- 关键方法：`needs_rescan()` 判断文件是否需要重新扫描，`insert_or_update()` 用 `ON CONFLICT(file_path)` 处理新增/更新，`get_project_by_composite_key()` 用于同项目多版本判定。

### parser.py
- `DocumentParser` 类：解析 PDF/DOC/DOCX 文件。
- PDF 用 `pdfplumber`；DOCX 用 `python-docx`（段落 + 表格，表格行以 `[TABLE]单元格\t单元格` 形式进入文本）；DOC 用 `docx2txt` 并尝试 `python-docx` 补表格。
- 正则抽取：项目名称、投标函日期（归一为 `YYYY-MM-DD`）、招标单位、投标单位。
- 招标单位匹配模式：招标人、招标单位、建设单位、业主单位、采购人。
- 投标单位匹配模式：投标人、投标单位、投标人名称、竞标单位、供应商、中标单位。
- 招标单位备选方案（按优先级）：
  1. 直接匹配：招标人/招标单位/建设单位等；
  2. 投标函“致：/致函：/送：/呈：/报：”后的收函单位；
  3. 投标函标题下方的抬头单位（如“投标函\n某某单位：”）。
- **投标文件过滤** (`is_bid_document`)：
  - 文件名排除：封套、封面、目录、封底、备忘、备注、注意事项、招标、格式、模板、样表、样张、关键点、答疑、澄清；
  - 正文必须含带章节编号（第X章/（一）/1./一、）的实质性章节之一：投标函、开标一览表、营业执照；
  - 命中投标函/开标一览表时，还需通过三要素校验：抬头单位 + 投标单位 + 日期（且年月与开标日期一致）；
  - 只有符合条件的文件才保存到数据库。
- **分项明细** (`_extract_itemized_details`)：按行切分表格（制表符/竖线/多空格），表头必须同时含“设备/产品名称”类列与“数量/单位”列；过滤空表、总价表、签字栏、无效设备名；`has_itemized_list` 由**实际提取到的明细条数**决定（`len(details) > 0`），不再单独做关键词判断。

### scanner.py
- `FileScanner` 类：支持可中断扫描、增量扫描。
- 使用 `threading.Event` 实现停止标志，`threading.Lock` 保护进度对象。
- 通过文件 hash（MD5）和 modified_time 检测文件变化；支持 `only_new` / `rescan_modified` 两种策略。
- 同一业务键（项目名称 + 投标单位 + 投标函日期）只保留修改时间最新的版本。
- 扫描在后台线程执行，通过 `on_progress` / `on_log` 回调向外抛状态。

### app.py
- `App` 类：customtkinter GUI 主窗口。
- 功能区域：数据库配置、扫描控制、查询条件、结果显示（Treeview）、操作按钮、日志输出。
- 扫描线程通过 `after(0, ...)` 回主线程更新 UI，保证界面不阻塞。
- 支持详情弹窗（基本信息 + 分项明细表格）、CSV 导出、右键菜单、统计信息。

## 数据库表结构

```sql
CREATE TABLE bidding_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,      -- 唯一索引，防止重复
    file_hash TEXT NOT NULL,             -- MD5 哈希，检测文件修改
    file_size INTEGER NOT NULL,
    modified_time REAL NOT NULL,
    scan_time REAL NOT NULL,
    project_name TEXT,
    bid_date TEXT,                       -- 投标函日期
    tender_org TEXT,
    bidder_org TEXT,
    has_itemized_list INTEGER            -- 1=有真实分项明细
);

CREATE TABLE itemized_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    device_name TEXT,
    brand TEXT,
    model TEXT,
    quantity TEXT,
    tax_rate TEXT,
    unit_price_tax_included TEXT,
    unit_price_tax_excluded TEXT,
    FOREIGN KEY (project_id) REFERENCES bidding_projects(id) ON DELETE CASCADE
);
```

索引：`bidder_org`、`tender_org`、`bid_date`、`itemized_details.project_id`。

## 关键技术点

1. **去重逻辑**：file_path 唯一索引 + hash 检测修改。
2. **可中断扫描**：threading.Event + 循环检查。
3. **线程安全**：进度更新使用 threading.Lock。
4. **GUI 不阻塞**：扫描在后台线程，通过 after() 回调更新 UI。
5. **外键级联**：`PRAGMA foreign_keys = ON` + 显式删除兜底 + 启动时孤儿明细清理，保证两表一致。

## 开发约定

1. 修改解析规则后，用 `sample_doc/` 中的真实文档做回归；不要复用 `tools/archive/` 里的旧脚本（路径硬编码、逻辑已过时）。
2. 修改表结构时同步更新 `_init_tables()` 与 `_migrate()`，保证旧库可平滑升级。
3. 运行测试：`pip install -r requirements-dev.txt` 后执行 `pytest`（用例在 `tests/`）。
4. 对外行为变更同步更新 README.md 与 CLAUDE.md。
