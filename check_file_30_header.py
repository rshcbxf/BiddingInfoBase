# -*- coding: utf-8 -*-
"""检查具体文件的表格解析"""
import sys
sys.path.insert(0, r'C:\Projects\BiddingInfoBase')

from bidding_gui.parser import DocumentParser
import sqlite3
import os

db_path = r"C:\Users\heqin\bidding_info.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT file_path FROM bidding_projects WHERE id = 30")
file_path = cursor.fetchone()[0]
conn.close()

parser = DocumentParser()

if os.path.exists(file_path):
    text = parser._parse_doc(file_path)
    lines = text.split('\n')

    # 查找包含制表符且包含"数量"或"单位"的行（表头特征）
    print("=== 查找可能的表头行 ===\n")
    for i, line in enumerate(lines):
        if '\t' in line and ('数量' in line or '单位' in line or '型号' in line or '品牌' in line):
            start = max(0, i - 1)
            end = min(len(lines), i + 5)
            print(f"--- 行{i+1} ---")
            for j in range(start, end):
                marker = ">>> " if j == i else "    "
                content = lines[j][:200].replace('\t', ' | ')
                print(f"{marker}{j+1}: {content}")
            print()
