# -*- coding: utf-8 -*-
"""检查分项明细数据质量"""
import sqlite3

db_path = r"C:\Users\heqin\bidding_info.db"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 查询分项明细数据
cursor.execute("""
    SELECT d.project_id, p.project_name, d.device_name, d.brand, d.model
    FROM itemized_details d
    JOIN bidding_projects p ON d.project_id = p.id
    LIMIT 30
""")
details = cursor.fetchall()

print("=== 分项明细数据示例 ===\n")
for detail in details:
    project_name = detail['project_name'][:30] if detail['project_name'] else 'N/A'
    device = detail['device_name'][:20] if detail['device_name'] else '(空)'
    brand = detail['brand'][:10] if detail['brand'] else '(空)'
    model = detail['model'][:10] if detail['model'] else '(空)'
    print(f"{project_name}... | {device} | {brand} | {model}")

# 统计数据质量
cursor.execute("""
    SELECT
        COUNT(*) as total,
        COUNT(CASE WHEN device_name IS NULL OR device_name = '' THEN 1 END) as no_device,
        COUNT(CASE WHEN brand IS NULL OR brand = '' THEN 1 END) as no_brand,
        COUNT(CASE WHEN model IS NULL OR model = '' THEN 1 END) as no_model
    FROM itemized_details
""")
stats = cursor.fetchone()

print(f"\n=== 数据质量统计 ===")
print(f"  总记录数：{stats['total']}")
print(f"  无设备名称：{stats['no_device']}")
print(f"  无品牌：{stats['no_brand']}")
print(f"  无型号：{stats['no_model']}")

conn.close()
