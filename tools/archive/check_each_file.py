# -*- coding: utf-8 -*-
"""检查具体文件的解析结果"""
import sys
sys.path.insert(0, r'C:\Projects\BiddingInfoBase')

from bidding_gui.parser import DocumentParser
import sqlite3
import os

db_path = r"C:\Users\heqin\bidding_info.db"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 获取所有有分项明细的记录
cursor.execute("""
    SELECT id, file_path, project_name
    FROM bidding_projects
    WHERE has_itemized_list = 1
""")
records = cursor.fetchall()

parser = DocumentParser()

print("=== 检查各文件的分项明细提取情况 ===\n")

for record in records:
    file_path = record['file_path']

    if not os.path.exists(file_path):
        continue

    try:
        result = parser.parse_file(file_path)

        print(f"ID={record['id']}: {record['project_name'][:40] if record['project_name'] else 'N/A'}...")
        print(f"  has_itemized_list: {result.has_itemized_list}")
        print(f"  提取明细数：{len(result.itemized_details)}")

        if result.itemized_details:
            print(f"  前 3 条明细:")
            for i, d in enumerate(result.itemized_details[:3]):
                print(f"    {i+1}. 设备:{d.device_name[:20] if d.device_name else '(空)'} | 品牌:{d.brand[:10] if d.brand else '(空)'} | 型号:{d.model[:10] if d.model else '(空)'}")
        print()

    except Exception as e:
        print(f"ID={record['id']}: 解析失败 - {e}")
        print()

conn.close()
