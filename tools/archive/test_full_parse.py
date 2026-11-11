# -*- coding: utf-8 -*-
"""测试完整的解析流程"""
import sys
sys.path.insert(0, r'C:\Projects\BiddingInfoBase')

from bidding_gui.parser import DocumentParser
import os
import sqlite3

db_path = r'C:\Users\heqin\bidding_info.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('SELECT file_path FROM bidding_projects WHERE id = 30')
file_path = cursor.fetchone()[0]
conn.close()

parser = DocumentParser()

if os.path.exists(file_path):
    text = parser._parse_doc(file_path)

    # 手动执行 _extract_itemized_details 的逻辑，添加调试输出
    details = []
    lines = text.split('\n')

    column_mapping = {
        '设备名称': 'device_name',
        '设备': 'device_name',
        '产品名称': 'device_name',
        '数量': 'quantity',
        '单位': 'unit',
        '型号': 'model',
        '品牌': 'brand',
    }

    required_quantity_columns = {'quantity', 'unit'}

    in_itemized_table = False
    header_indices = {}
    consecutive_data_rows = 0
    table_ended = False
    has_valid_table = False

    print("=== 开始解析 ===\n")

    for i, line in enumerate(lines):
        line_stripped = line.strip()

        if line_stripped.startswith('[TABLE]'):
            line_stripped = line_stripped[7:]

        # 检查是否进入分项/明细章节
        if '分项' in line_stripped and '明细' in line_stripped:
            print(f"行{i+1}: 检测到分项/明细章节")

        # 尝试解析表格行
        if '\t' in line_stripped:
            cells = [c.strip() for c in line_stripped.split('\t') if c.strip()]
        elif '|' in line_stripped:
            cells = [c.strip() for c in line_stripped.split('|') if c.strip()]
        else:
            import re
            cells = re.split(r'\s{2,}', line_stripped)
            cells = [c.strip() for c in cells if c.strip()]

        if len(cells) < 2:
            continue

        # 检查是否是表头
        is_header = False
        matched_columns = set()
        for cell in cells:
            for cn_name, en_name in column_mapping.items():
                if cn_name in cell:
                    matched_columns.add(cn_name)
                    is_header = True

        if is_header and len(matched_columns) >= 3:
            print(f"行{i+1}: 检测到表头，匹配列={matched_columns}")

            header_indices = parser._match_header_columns(cells, column_mapping)
            print(f"  表头索引：{header_indices}")

            has_device_name = 'device_name' in header_indices
            has_quantity = bool(header_indices.keys() & required_quantity_columns)

            print(f"  has_device_name={has_device_name}, has_quantity={has_quantity}")

            if has_device_name and has_quantity:
                if in_itemized_table and len(details) == 0:
                    print(f"  -> 切换到新表格")
                elif not in_itemized_table:
                    in_itemized_table = True
                    has_valid_table = True
                    print(f"  -> 开始新表格")

                consecutive_data_rows = 0
            else:
                header_indices = {}
                print(f"  -> 不是设备明细表，跳过")
            continue

        # 数据行处理
        if in_itemized_table and header_indices:
            max_idx = max(header_indices.values()) if header_indices else 0

            if len(cells) > max_idx or (len(cells) >= 2 and header_indices):
                # 提取数据
                detail_data = {}
                for field, idx in header_indices.items():
                    if idx < len(cells):
                        value = cells[idx].strip()
                        if value:
                            detail_data[field] = value

                print(f"行{i+1}: 数据行 -> {detail_data.get('device_name', 'N/A')}")

                # 验证设备名称
                invalid_keywords = ['签字', '盖章', '备注', '税率', '投标', '招标', '公司',
                                   '序号', '项目名称', '法定代表人']
                device_name = detail_data.get('device_name', '')

                is_valid = True
                if device_name:
                    if len(device_name.strip()) <= 2:
                        is_valid = False
                    for kw in invalid_keywords:
                        if kw in device_name:
                            is_valid = False
                            break

                if is_valid and any(detail_data.get(f) for f in ['device_name', 'brand', 'model', 'quantity']):
                    details.append(detail_data)
                    consecutive_data_rows += 1
                    print(f"  -> 添加有效数据")
                else:
                    print(f"  -> 无效数据，跳过")

    print(f"\n=== 解析完成 ===")
    print(f"提取到 {len(details)} 条明细")
    for d in details[:5]:
        print(f"  {d}")
