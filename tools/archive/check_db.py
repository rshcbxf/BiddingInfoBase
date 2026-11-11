# -*- coding: utf-8 -*-
import sqlite3

db_path = r"C:\Users\heqin\bidding_info.db"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 查询所有 has_itemized_list=1 的记录
print("=== has_itemized_list=1 的记录 ===")
cursor.execute("""
    SELECT id, project_name, bidder_org, has_itemized_list
    FROM bidding_projects
    WHERE has_itemized_list = 1
""")
records = cursor.fetchall()

for record in records:
    project_id = record['id']
    # 检查是否有分项明细数据
    cursor.execute("SELECT COUNT(*) as count FROM itemized_details WHERE project_id = ?", (project_id,))
    detail_count = cursor.fetchone()['count']

    status = "[OK]" if detail_count > 0 else "[MISSING]"
    print(f"ID={project_id}: {record['project_name'][:30] if record['project_name'] else 'N/A'}... - {status} (明细数：{detail_count})")

# 统计
print("\n=== 统计 ===")
cursor.execute("SELECT COUNT(*) FROM bidding_projects WHERE has_itemized_list = 1")
total_with_itemized = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(DISTINCT project_id)
    FROM itemized_details
""")
projects_with_details = cursor.fetchone()[0]

print(f"has_itemized_list=1 的记录数：{total_with_itemized}")
print(f"有分项明细数据的项目数：{projects_with_details}")
print(f"有标记但无明细数据的记录数：{total_with_itemized - projects_with_details}")

# 查看具体的 itemized_details 数据
print("\n=== 分项明细数据示例 ===")
cursor.execute("SELECT * FROM itemized_details LIMIT 5")
details = cursor.fetchall()
for detail in details:
    device = detail['device_name'].encode('gbk', errors='replace').decode('gbk') if detail['device_name'] else ''
    brand = detail['brand'].encode('gbk', errors='replace').decode('gbk') if detail['brand'] else ''
    model = detail['model'].encode('gbk', errors='replace').decode('gbk') if detail['model'] else ''
    print(f"  project_id={detail['project_id']}: {device} | {brand} | {model}")

conn.close()
