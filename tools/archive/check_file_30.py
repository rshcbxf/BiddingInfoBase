# -*- coding: utf-8 -*-
"""检查具体文件的文本内容"""
import sys
sys.path.insert(0, r'C:\Projects\BiddingInfoBase')

from bidding_gui.parser import DocumentParser
import sqlite3
import os

db_path = r"C:\Users\heqin\bidding_info.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查 ID=30 的文件
cursor.execute("SELECT file_path, project_name FROM bidding_projects WHERE id = 30")
record = cursor.fetchone()
file_path = record[0]
project_name = record[1]

print(f"文件：{project_name[:50] if project_name else 'N/A'}...")
print(f"路径：{file_path}")
print(f"存在：{os.path.exists(file_path)}")

parser = DocumentParser()

if os.path.exists(file_path):
    text = parser._parse_doc(file_path)
    lines = text.split('\n')

    # 查找包含"明细"或"清单"的行
    print("\n=== 查找表格相关内容 ===\n")
    for i, line in enumerate(lines):
        if '明细' in line or '清单' in line or '报价' in line or '[TABLE]' in line:
            start = max(0, i - 1)
            end = min(len(lines), i + 5)
            print(f"--- 行{i+1} ---")
            for j in range(start, end):
                marker = ">>> " if j == i else "    "
                content = lines[j][:100].replace('\t', '\\t')
                print(f"{marker}{j+1}: {content}")
            print()

conn.close()
