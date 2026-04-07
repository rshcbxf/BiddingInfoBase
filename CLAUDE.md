# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

投标文件信息管理系统 - 跨平台 GUI 程序，用于扫描、解析和管理投标文件信息。

## 运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 运行程序
python -m bidding_gui.main
# 或
python bidding_gui/main.py
```

## 项目结构

```
C:\Projects\BiddingInfoBase\
├── bidding_gui/
│   ├── __init__.py         # 包初始化，导出公共接口
│   ├── main.py             # 程序入口
│   ├── app.py              # GUI 主窗口（customtkinter）
│   ├── database.py         # SQLite 数据库操作
│   ├── parser.py           # 文档解析器（PDF/DOC/DOCX）
│   └── scanner.py          # 文件扫描器（支持中断、增量扫描）
├── requirements.txt
└── CLAUDE.md
```

## 核心模块说明

### database.py
- `Database` 类：SQLite 数据库操作
- `BiddingProject` 数据模型：包含 file_path（唯一索引）、file_hash 用于去重
- 关键方法：`needs_rescan()` 判断文件是否需要重新扫描，`insert_or_update()` 自动处理新增/更新

### parser.py
- `DocumentParser` 类：解析 PDF/DOC/DOCX 文件
- 使用 regex 匹配关键词提取：项目名称、开标日期、招标单位、投标单位、招标内容
- PDF 使用 `pdfplumber`，DOCX 使用 `python-docx`，DOC 使用 `docx2txt`
- 投标单位匹配模式：投标人、投标单位、投标人名称、竞标单位、供应商、中标单位
- 招标单位匹配模式：招标人、招标单位、建设单位、业主单位、采购人
- 招标单位备选方案（按优先级）：
  1. 直接匹配：招标人/招标单位/建设单位等
  2. 投标函"致："后的收函单位
  3. 投标函标题下方的抬头单位（如"投标函\n某某单位："）
- **投标文件过滤** (`is_bid_document`)：
  - 文件名包含：投标、标书、响应文件、询价
  - 或内容包含：投标人、投标单位、投标函、报价表、投标报价、开标一览表、投标书
  - 只有符合条件的文件才保存到数据库

### scanner.py
- `FileScanner` 类：支持可中断扫描、增量扫描
- 使用 `threading.Event` 实现停止标志
- 通过文件 hash 和 modified_time 检测文件变化

### app.py
- `App` 类：customtkinter GUI 主窗口
- 功能区域：数据库配置、扫描控制、查询条件、结果显示、日志输出
- 扫描在后台线程执行，通过 `after()` 更新 UI

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
    bid_date TEXT,
    tender_org TEXT,
    bidder_org TEXT,
    bid_content TEXT
)
```

## 关键技术点

1. **去重逻辑**：file_path 唯一索引 + hash 检测修改
2. **可中断扫描**：threading.Event + 循环检查
3. **线程安全**：进度更新使用 threading.Lock
4. **GUI 不阻塞**：扫描在后台线程，通过 after() 回调更新 UI
