# 投标文件信息管理系统（BiddingInfoBase）

一个基于 Python + [customtkinter](https://github.com/TomSchimansky/CustomTkinter) 的跨平台桌面程序：递归扫描指定文件夹中的 **PDF / DOC / DOCX** 文档，自动识别其中的**投标文件**，抽取项目名称、投标函日期、招标单位、投标单位以及**分项报价明细**，存入 SQLite，并提供图形界面完成查询、筛选、详情查看与 CSV 导出。

```
选择文件夹 → 识别投标文件 → 解析关键字段与分项明细 → SQLite 入库 → 查询 / 详情 / 导出
```

## 功能特性

- **多格式解析**：PDF（pdfplumber）、DOCX（python-docx，含表格）、DOC（docx2txt + python-docx 兜底）。
- **投标文件智能识别**：按文件名排除招标文件、封套、模板、目录等；再要求文档含“投标函 / 开标一览表 / 营业执照”等带编号的实质性章节；最后校验抬头单位、投标单位、日期三要素，减少误判。
- **字段抽取**：项目名称、投标函日期（归一为 `YYYY-MM-DD`）、招标单位（三级兜底）、投标单位。
- **分项明细提取**：从报价/设备清单类表格中提取设备名称、品牌、型号、数量、税率、含税单价、不含税单价；自动排除空表、总价表、签字栏等非设备表格。
- **增量扫描**：用 MD5 + 修改时间判断文件是否变化，未变化则跳过；支持**随时中断**，进度与日志实时回显。
- **版本合并**：当“项目名称 + 投标单位 + 投标函日期”相同的多个版本进入库时，只保留修改时间最新的一份。
- **数据一致性**：启用 SQLite 外键约束并做孤儿明细清理，删除主记录时自动清理其分项明细。
- **GUI 操作**：数据库配置、扫描控制、组合查询、结果表格、详情窗口、CSV 导出、数据库统计、日志保存。

## 环境要求

- Python **3.9+**（开发与验证环境为 3.11；3.12+ 亦可，需自行确认依赖兼容性）
- Windows / macOS / Linux（customtkinter 跨平台）
- SQLite 由 Python 内置，无需单独安装

## 安装

```bash
git clone <仓库地址>
cd BiddingInfoBase

python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## 运行

```bash
python -m bidding_gui.main
# 或
python bidding_gui/main.py
```

首次启动会在**用户主目录**自动创建数据库 `bidding_info.db`（例如 `C:\Users\<用户>\bidding_info.db`），可在界面顶部的“数据库配置”区域修改路径。

## 使用说明

### 1. 数据库配置

- **浏览**：选择已有的 `.db` 文件；**重建**：删除当前库文件并重新建空库（**会清空已有数据，操作前请确认或备份**）。
- 右侧实时显示统计：记录数 / 不同投标单位数 / 不同招标单位数。

### 2. 扫描

1. 点击“扫描控制”区域的**浏览**选择文件夹（会递归扫描所有子目录）；
2. 勾选扫描策略（默认“仅扫描新文件”即为推荐用法）；
3. 点击**开始扫描**，进度与日志实时更新，可点**停止**中断；
4. 扫描结束后自动刷新统计与结果列表。

两种复选框的实际行为：

| 仅扫描新文件 | 重新解析已修改文件 | 实际行为 |
|:---:|:---:|---|
| ☑ | ☐ | **增量（默认，推荐）**：新增文件、内容发生变化的文件入库，其余跳过 |
| ☑ | ☑ | 与上一行相同，仅在日志中额外提示“文件已修改” |
| ☐ | ☐ | 只补新增文件，已入库的文件即使改动也跳过 |
| ☐ | ☑ | **全量重解析**：所有已入库文件重新解析（升级解析规则后刷新数据用，耗时） |

> 注意：“仅扫描新文件”实际语义是“跳过已入库且未变化的文件”，内容变化的文件仍会重新解析。

### 3. 查询与结果

- 查询条件：**投标单位**（模糊匹配）、**分项明细**（全部 / 是 / 否）、**投标函日期**区间（`YYYY-MM-DD`）。
- 按钮：查询 / 清空条件 / 显示全部 / 导出 CSV。
- 结果列表展示 ID、项目名称、投标函日期、招标单位、投标单位、有无分项明细、文件路径、扫描时间。
- **查看详情**：选中记录后点击按钮或右键菜单，弹窗展示基本信息与分项明细表。
- **删除选中**：删除记录及其分项明细（不可恢复）。
- **清除无效记录**：删除磁盘上已不存在的文件对应的记录。
- **导出 CSV**：有选中行时导出选中，否则导出当前列表全部；文件为 `UTF-8 BOM`，可直接用 Excel 打开。CSV 仅包含列表中的 8 个字段，不含分项明细。

### 4. 日志

日志框记录扫描、跳过原因、错误等；可清空或另存为 `.txt`。

## 目录结构

```
BiddingInfoBase/
├── bidding_gui/              # 程序包
│   ├── __init__.py           # 导出公共接口、版本号
│   ├── main.py               # 程序入口
│   ├── app.py                # GUI 主窗口（customtkinter）
│   ├── database.py           # SQLite 数据访问层
│   ├── parser.py             # 文档解析与信息抽取
│   └── scanner.py            # 扫描调度（增量、可中断）
├── tools/archive/            # 开发期一次性调试脚本（已归档，不参与运行）
├── sample_doc/               # 本地测试语料（真实招标/投标文档，未纳入版本库）
├── requirements.txt
├── README.md                 # 本文件
├── CLAUDE.md                 # 面向 AI 编码助手的仓库指南
├── fix_plan.md               # “分项明细”问题的分析与修复方案
├── fix_summary.md            # 该问题的修复结果与数据对比
└── .gitignore
```

## 架构与数据流

```
┌─────────────┐   文件夹路径
│  app.py     │ ─────────────┐
│ (GUI 主线程) │              ▼
└─────────────┘      ┌──────────────┐   os.walk 递归收集 .pdf/.doc/.docx
        ▲            │ scanner.py   │ ───────────────────────────────┐
        │ after()    │ (后台 daemon │                                ▼
        │ 回调        │  线程)       │  每个文件：计算 MD5 + mtime/size
        └────────────┘              │  → 查库判断是否需要扫描（增量）
                                    │  → parser.parse_file 解析全文
                                    │  → is_bid_document 过滤非投标文件
                                    │  → 复合键查重（多版本只留最新）
                                    │  → database 写入主表 + 明细表
                                    ▼
                             ┌─────────────┐
                             │ database.py │  SQLite: bidding_projects
                             │             │          itemized_details
                             └─────────────┘
```

- **线程模型**：扫描在后台 `daemon` 线程执行；进度/日志通过 `after(0, ...)` 投递回主线程更新 UI，界面不阻塞；`threading.Event` 实现停止，`threading.Lock` 保护进度对象。
- **增量判定**：`file_path` 唯一约束 + `file_hash`（MD5）+ `modified_time` 双判据。
- **版本合并**：扫描器以“项目名称 + 投标单位 + 投标函日期”为业务键查重，保留修改时间最新的文件。

## 核心模块

| 模块 | 职责 |
|---|---|
| `bidding_gui/app.py` | 主窗口布局（数据库配置 / 扫描控制 / 查询 / 结果表 / 操作按钮 / 日志）、后台扫描调度、详情弹窗、CSV 导出 |
| `bidding_gui/scanner.py` | 递归收集文件、增量与重扫策略、非投标文件跳过、多版本替换、明细入库、清理无效记录 |
| `bidding_gui/parser.py` | PDF/DOC/DOCX 取文、投标文件判定、字段正则抽取、分项明细表格识别、日期归一 |
| `bidding_gui/database.py` | 建表/迁移、去重 upsert、查询与统计、分项明细读写、外键级联与孤儿清理 |

## 解析规则详解

### 投标文件识别（`DocumentParser.is_bid_document`）

1. **文件名排除**：文件名命中 `封套 / 封面 / 标书封面 / 投标函封面 / 目录 / 封底 / 备忘 / 备注 / 注意事项 / 招标 / 格式 / 模板 / 样表 / 样张 / 关键点 / 答疑 / 澄清` 之一 → 直接排除。
2. **实质性章节**：正文必须含带章节编号（`第X章`、`（一）`、`1.`、`一、` 等）的 **投标函 / 开标一览表 / 营业执照** 之一。
3. **三要素校验**（命中投标函或开标一览表时）：要求同时存在
   - 抬头单位（`致：XXX`、含“招标人/招标单位/建设单位…”的行、或“某某公司：”式抬头）；
   - 投标单位（`投标人：`、`投标单位：`、`投标人名称：` 等）；
   - 日期，且年月与文档开标日期一致。

### 字段抽取

| 字段 | 主要匹配 | 兜底策略 |
|---|---|---|
| 项目名称 | `项目名称/工程项目名称/工程名称/标段名称：` | 取文档第一行（长度 > 5） |
| 投标函日期 | 投标函附近日期、`投标人：` 后的日期、`日期：`、`签署日期：` | 全文第一个日期；归一为 `YYYY-MM-DD` |
| 招标单位 | `招标人/招标单位/建设单位/业主单位/采购人：` | ① 投标函 `致：/致函：/送：/呈：/报：` 后的收函单位；② 投标函标题下方的抬头单位 |
| 投标单位 | `投标人/投标单位/投标人名称/竞标单位/供应商/中标单位：` | — |

### 分项明细提取

- 表格行来源：DOCX 表格被解析为 `[TABLE]单元格\t单元格`；同时兼容制表符、`|`、连续多空格分隔。
- **表头判定**：必须同时包含“设备/产品名称”类列与“数量”或“单位”列，否则不视为设备明细表；只有“总价”而无“单位”的汇总表会被排除。
- **数据行过滤**：设备名称长度 ≤ 2、纯数字、或命中签字/盖章/备注/税率/公司/合计等无效关键词的行会被丢弃。
- 遇到“合计/总计/小计/汇总”结束当前表格；空表模板会跳过并继续寻找后续真正的明细表；连续过多数据行会判定为其他表格并停止。
- 最终只有**成功识别到表格且至少提取出一条有效明细**时，`has_itemized_list` 才为真（即该标记与明细数据严格一致）。

## 数据库设计

```sql
-- 一个投标文件一条记录
CREATE TABLE bidding_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,   -- 唯一约束，防止重复入库
    file_hash TEXT NOT NULL,          -- MD5，用于增量判定
    file_size INTEGER NOT NULL,
    modified_time REAL NOT NULL,
    scan_time REAL NOT NULL,
    project_name TEXT,
    bid_date TEXT,                    -- 投标函日期（YYYY-MM-DD）
    tender_org TEXT,                  -- 招标单位
    bidder_org TEXT,                  -- 投标单位
    has_itemized_list INTEGER         -- 1=有真实分项明细，0=无
);

-- 一条设备/分项明细一行
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

CREATE INDEX idx_bidder_org ON bidding_projects(bidder_org);
CREATE INDEX idx_tender_org ON bidding_projects(tender_org);
CREATE INDEX idx_bid_date   ON bidding_projects(bid_date);
CREATE INDEX idx_project_id ON itemized_details(project_id);
```

- **外键级联**：连接建立时执行 `PRAGMA foreign_keys = ON`，保证删除主记录时明细级联删除；`delete_by_id/delete_by_ids` 同时做显式兜底删除。
- **孤儿清理**：打开数据库时自动清除 `project_id` 已不存在的历史孤儿明细。
- **结构迁移**：旧版库中的 `bid_content` 大文本字段会自动迁移为 `has_itemized_list` 标记（SQLite 不支持删列，采用“建新表 → 搬数据 → 改名”重建）。

## 已知限制

1. **扫描版 PDF（无文本层）无法解析**：只会得到 `[PDF 解析错误]` 或空文本，需先做 OCR；图片格式（jpg/png）不在扫描范围内。
2. **只支持 `.pdf / .doc / .docx`**：`xlsx`、`zip` 等不会入库。
3. **表格识别基于文本启发式**：切分时会丢弃空单元格，报价表中间有空列时可能列错位；合并单元格、多行表头识别能力有限。
4. **日期抽取的兜底规则**：当投标函附近找不到日期时，会退化为取全文第一个日期，未必是投标函落款日期；日期归一目前识别“年月日 / 斜杠 / 点 / 短横线”等常见写法，并统一补零为 `YYYY-MM-DD`，非常规写法会保留原样。
5. **多版本合并有条件**：仅当项目名称、投标单位、日期三者都非空时才生效，缺字段的文件可能重复入库。
6. **CSV 不含分项明细**：仅导出结果列表的 8 个字段。
7. **单线程串行扫描**：超大目录或大体积 PDF 时速度较慢、内存占用较高。
8. **无自动化测试**：当前验证依赖手工脚本与真实语料回归。

## 常见问题（FAQ）

**Q：为什么某个文档扫描后没有入库？**
看日志中的 `[SKIP] 非投标文件，跳过`。常见原因：文件名命中排除词（如含“招标/格式/目录”）、缺少带编号的“投标函/开标一览表/营业执照”章节、或三要素（抬头单位/投标单位/日期）校验未通过。

**Q：为什么记录显示“分项明细：否”，但文档里明明有报价表？**
明细表需要同时具备“设备/产品名称”列和“数量/单位”列；如果表格只有总价、是空表模板、或表头写法特殊（如合并单元格），可能未被识别。

**Q：升级了解析规则，如何刷新已有数据？**
取消“仅扫描新文件”、勾选“重新解析已修改文件”做一次全量扫描；或在备份后重建数据库再全量扫描。

**Q：数据库文件在哪？可以换吗？**
默认在用户主目录 `bidding_info.db`，界面顶部可浏览切换或重建。删除该文件等同于清空数据。

**Q：Windows 上提示缺少模块？**
确认已在虚拟环境中执行 `pip install -r requirements.txt`；本项目验证环境为 Python 3.11。

## 开发说明

- **修改解析规则**：编辑 `bidding_gui/parser.py` 中的 `PATTERNS`、`is_bid_document`、`_extract_itemized_details` 等；建议用 `sample_doc/` 中的真实文档做回归对比。
- **修改表结构**：在 `database.py` 的 `_init_tables()` 中调整建表语句，并在 `_migrate()` 中补齐旧库迁移逻辑，保证已有数据库可平滑升级。
- **历史脚本**：根目录原有的 19 个调试脚本已归档到 [`tools/archive/`](tools/archive/README.md)，其中硬编码了作者本机路径、且复制了旧版解析逻辑，仅供追溯，不建议复用。
- **测试建议**：目前无正式测试体系，可考虑为 `parser.is_bid_document`、明细提取、数据库级联与迁移补充 pytest 用例。

## 版本

当前版本：**1.0.0**（见 `bidding_gui/__init__.py`）。

## 许可证

未指定许可证。如需开源发布，请补充 `LICENSE` 文件。
