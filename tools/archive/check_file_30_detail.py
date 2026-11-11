# -*- coding: utf-8 -*-
"""检查具体文件的解析结果"""
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
project_name = record[1] if record[1] else 'N/A'

print(f"文件：{project_name[:50]}...")

parser = DocumentParser()

if os.path.exists(file_path):
    result = parser.parse_file(file_path)

    print(f"has_itemized_list: {result.has_itemized_list}")
    print(f"提取明细数：{len(result.itemized_details)}")

    print("\n=== 所有明细数据 ===")
    for i, d in enumerate(result.itemized_details):
        print(f"{i+1}. 设备:{d.device_name[:30] if d.device_name else '(空)'} | 品牌:{d.brand[:10] if d.brand else '(空)'} | 型号:{d.model[:10] if d.model else '(空)'} | 数量:{d.quantity[:10] if d.quantity else '(空)'}")

conn.close()
