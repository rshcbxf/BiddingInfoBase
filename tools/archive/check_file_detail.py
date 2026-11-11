# -*- coding: utf-8 -*-
"""检查具体文件解析结果"""
import sys
sys.path.insert(0, r'C:\Projects\BiddingInfoBase')

from bidding_gui.parser import DocumentParser
import sqlite3
import os

db_path = r"C:\Users\heqin\bidding_info.db"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 获取 ID=2 的文件路径
cursor.execute("SELECT file_path, project_name FROM bidding_projects WHERE id = 2")
record = cursor.fetchone()

print(f"文件路径：{record['file_path']}")
print(f"项目名称：{record['project_name']}")
print(f"文件存在：{os.path.exists(record['file_path'])}")

parser = DocumentParser()

# 重新解析文件
text = parser._parse_doc(record['file_path'])
print(f"\n文本长度：{len(text)}")

# 提取分项明细
details = parser._extract_itemized_details(text)
print(f"\n提取到 {len(details)} 条明细")

print("\n=== 明细数据 ===")
for i, d in enumerate(details[:15]):
    print(f"{i+1}. {d.device_name} | {d.brand} | {d.model} | {d.quantity} | {d.unit_price_tax_included}")

conn.close()
