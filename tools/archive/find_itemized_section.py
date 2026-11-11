# -*- coding: utf-8 -*-
"""检查文件文本内容"""
import sys
sys.path.insert(0, r'C:\Projects\BiddingInfoBase')

from bidding_gui.parser import DocumentParser
import sqlite3
import os

db_path = r"C:\Users\heqin\bidding_info.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT file_path FROM bidding_projects WHERE id = 2")
record = cursor.fetchone()
file_path = record[0]

print(f"文件路径：{file_path}")
print(f"文件存在：{os.path.exists(file_path)}")

parser = DocumentParser()

if os.path.exists(file_path):
    text = parser._parse_doc(file_path)

    # 查找包含"分项"或"明细"的部分
    lines = text.split('\n')

    print(f"\n文本行数：{len(lines)}")
    print("\n=== 查找包含'分项'或'明细'的行 ===\n")
    for i, line in enumerate(lines):
        if '分项' in line or '明细' in line or '报价' in line or '清单' in line or 'TABLE' in line.upper():
            # 显示该行及其前后各 5 行
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            print(f"--- 第{i+1}行 ---")
            for j in range(start, end):
                marker = ">>> " if j == i else "    "
                print(f"{marker}{j+1}: {lines[j][:100]}")
            print()
else:
    print(f"文件不存在")

conn.close()
