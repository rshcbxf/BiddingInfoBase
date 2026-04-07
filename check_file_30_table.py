# -*- coding: utf-8 -*-
"""检查具体文件的表格内容"""
import sys
sys.path.insert(0, r'C:\Projects\BiddingInfoBase')

from bidding_gui.parser import DocumentParser
import os

db_path = r"C:\Users\heqin\bidding_info.db"

parser = DocumentParser()

# ID=30 的文件
file_path = r"C:/DATA/Document/2025 年高考工作\251202 广电项目\2025 年射频测试设备及演播室设备采购项目 - 投标文件.docx"

# 尝试使用数据库中的路径
import sqlite3
db_path = r"C:\Users\heqin\bidding_info.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT file_path FROM bidding_projects WHERE id = 30")
db_file_path = cursor.fetchone()[0]
conn.close()

print(f"数据库路径：{db_file_path}")
print(f"指定路径：{file_path}")
print(f"数据库路径存在：{os.path.exists(db_file_path)}")
print(f"指定路径存在：{os.path.exists(file_path)}")

# 使用存在的路径
if os.path.exists(db_file_path):
    file_path = db_file_path
elif not os.path.exists(file_path):
    print("两个路径都不存在")
    sys.exit(1)

print(f"文件存在：{os.path.exists(file_path)}")

if os.path.exists(file_path):
    text = parser._parse_doc(file_path)
    lines = text.split('\n')

    # 查找包含制表符的行（表格数据）
    print("\n=== 包含制表符的表格行 ===\n")
    for i, line in enumerate(lines):
        if '\t' in line and len(line) > 10:
            # 显示该行及其前后各 2 行
            start = max(0, i - 1)
            end = min(len(lines), i + 2)
            print(f"--- 行{i+1} ---")
            for j in range(start, end):
                marker = ">>> " if j == i else "    "
                content = lines[j][:150].replace('\t', ' | ')
                print(f"{marker}{j+1}: {content}")
            print()
