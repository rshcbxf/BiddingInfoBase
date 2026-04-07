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

    # 查看第 1300-1320 行的内容
    print("=== 第 1300-1320 行 ===\n")
    for i in range(1300, min(1325, len(lines))):
        content = lines[i][:200].replace('\t', ' | ')
        print(f"{i+1}: {content}")
