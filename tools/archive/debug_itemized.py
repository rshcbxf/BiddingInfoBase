# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'C:\Projects\BiddingInfoBase')

from bidding_gui.parser import DocumentParser
import sqlite3

db_path = r"C:\Users\heqin\bidding_info.db"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 查询 has_itemized_list=1 但没有明细数据的记录
cursor.execute("""
    SELECT id, project_name, file_path
    FROM bidding_projects
    WHERE has_itemized_list = 1
    AND id NOT IN (SELECT DISTINCT project_id FROM itemized_details)
    LIMIT 5
""")
records = cursor.fetchall()

parser = DocumentParser()

print("=== 检查有标记但无明细数据的文件 ===\n")

for record in records:
    print(f"ID={record['id']}")
    print(f"  项目名称：{record['project_name'][:50] if record['project_name'] else 'N/A'}...")
    print(f"  文件路径：{record['file_path']}")

    # 检查文件是否存在
    import os
    if not os.path.exists(record['file_path']):
        print(f"  [SKIP] 文件不存在")
        continue

    # 重新解析文件
    try:
        text = parser._parse_doc(record['file_path'])
        print(f"  文本长度：{len(text)}")

        # 检查是否包含分项/明细关键词
        import re
        patterns = [
            r'(?:分项 | 明细).*(?:表 | 清单)',
            r'(?:表 | 清单).*(?:分项 | 明细)',
            r'分项报价',
            r'报价明细',
            r'设备明细',
            r'货物明细',
            r'清单明细',
        ]

        print(f"  分项/明细检测:")
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                print(f"    - 匹配：{pattern} -> {repr(match.group()[:50])}")
                break
        else:
            print(f"    - 未匹配任何分项/明细模式")

        # 尝试提取明细
        details = parser._extract_itemized_details(text)
        print(f"  提取到的明细数：{len(details)}")

        if details:
            for d in details[:3]:
                print(f"    - {d.device_name} | {d.brand} | {d.model}")

    except Exception as e:
        print(f"  [ERROR] 解析失败：{e}")

    print()

conn.close()
