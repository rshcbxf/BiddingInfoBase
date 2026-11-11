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

parser = DocumentParser()

if os.path.exists(file_path):
    text = parser._parse_doc(file_path)

    # 查找包含 TABLE 的行
    lines = text.split('\n')

    print("=== 查找包含'TABLE'的行 ===\n")
    for i, line in enumerate(lines):
        if 'TABLE' in line.upper() or '分项' in line or '明细' in line or '报价' in line or '清单' in line:
            print(f"{i+1}: {repr(line[:150])}")

conn.close()
