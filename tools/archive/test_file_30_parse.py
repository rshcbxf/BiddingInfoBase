# -*- coding: utf-8 -*-
"""测试文件 30 的解析"""
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

    # 模拟解析逻辑
    column_mapping = {
        '设备名称': 'device_name',
        '设备': 'device_name',
        '产品名称': 'device_name',
        '数量': 'quantity',
        '单位': 'unit',
        '型号': 'model',
        '品牌': 'brand',
    }

    print("=== 查找第 1304 行附近的表头 ===\n")

    for i in range(1300, 1330):
        if i >= len(lines):
            break
        line = lines[i].strip()
        if line.startswith('[TABLE]'):
            line = line[7:]

        if '\t' in line:
            cells = [c.strip() for c in line.split('\t') if c.strip()]
            print(f"行{i+1}: 表格，单元格数={len(cells)}")
            print(f"  内容：{cells[:5]}")

            # 检查是否匹配表头
            matched = set()
            for cell in cells:
                for cn, en in column_mapping.items():
                    if cn in cell:
                        matched.add(cn)
            if matched:
                print(f"  匹配列：{matched}")
            print()
