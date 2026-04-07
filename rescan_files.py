# -*- coding: utf-8 -*-
"""重新解析文件并更新数据库"""
import sys
import os
sys.path.insert(0, r'C:\Projects\BiddingInfoBase')

from bidding_gui.parser import DocumentParser
import sqlite3

db_path = r"C:\Users\heqin\bidding_info.db"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 获取所有之前标记为 has_itemized_list=1 的记录
cursor.execute("SELECT id, file_path, project_name FROM bidding_projects")
records = cursor.fetchall()

parser = DocumentParser()

updated_count = 0
missing_count = 0

print("=== 重新解析文件并更新数据库 ===\n")

for record in records:
    file_path = record['file_path']

    # 检查文件是否存在
    if not os.path.exists(file_path):
        continue

    try:
        # 重新解析文件
        result = parser.parse_file(file_path)

        # 更新数据库
        has_itemized = 1 if result.has_itemized_list else 0
        cursor.execute("UPDATE bidding_projects SET has_itemized_list = ? WHERE id = ?", (has_itemized, record['id']))

        # 如果有分项明细，保存到数据库
        if result.has_itemized_list and result.itemized_details:
            # 删除原有的分项明细
            cursor.execute("DELETE FROM itemized_details WHERE project_id = ?", (record['id'],))

            # 插入新的分项明细
            for detail in result.itemized_details:
                cursor.execute("""
                    INSERT INTO itemized_details
                    (project_id, device_name, brand, model, quantity, tax_rate,
                     unit_price_tax_included, unit_price_tax_excluded)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (record['id'], detail.device_name, detail.brand, detail.model,
                      detail.quantity, detail.tax_rate, detail.unit_price_tax_included,
                      detail.unit_price_tax_excluded))

            print(f"[OK] {record['project_name'][:40] if record['project_name'] else 'N/A'}... - {len(result.itemized_details)} 条明细")
            updated_count += 1
        elif result.has_itemized_list:
            print(f"[WARN] {record['project_name'][:40] if record['project_name'] else 'N/A'}... - 标记为 True 但无明细数据")
        else:
            print(f"[SKIP] {record['project_name'][:40] if record['project_name'] else 'N/A'}... - 无分项明细")

    except Exception as e:
        print(f"[ERROR] {record['project_name'][:40] if record['project_name'] else 'N/A'}... - {e}")
        missing_count += 1

conn.commit()

# 统计结果
cursor.execute("SELECT COUNT(*) FROM bidding_projects WHERE has_itemized_list = 1")
has_itemized = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM itemized_details")
details_count = cursor.fetchone()[0]

print(f"\n=== 统计 ===")
print(f"  成功更新：{updated_count}")
print(f"  无明细数据：{missing_count}")
print(f"  has_itemized_list=1: {has_itemized}")
print(f"  分项明细记录数：{details_count}")

conn.close()
