# -*- coding: utf-8 -*-
"""清理数据库并重新扫描"""
import sqlite3
import os

db_path = r"C:\Users\heqin\bidding_info.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查看当前数据库状态
cursor.execute("SELECT COUNT(*) FROM bidding_projects")
total_records = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM bidding_projects WHERE has_itemized_list = 1")
has_itemized = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM itemized_details")
details_count = cursor.fetchone()[0]

print(f"当前数据库状态:")
print(f"  总记录数：{total_records}")
print(f"  has_itemized_list=1: {has_itemized}")
print(f"  分项明细记录数：{details_count}")

# 重置所有记录的 has_itemized_list 为 0
cursor.execute("UPDATE bidding_projects SET has_itemized_list = 0")
conn.commit()

# 删除所有分项明细数据
cursor.execute("DELETE FROM itemized_details")
conn.commit()

print(f"\n已重置:")
print(f"  所有记录的 has_itemized_list 设为 0")
print(f"  已删除所有分项明细数据")

# 验证
cursor.execute("SELECT COUNT(*) FROM bidding_projects WHERE has_itemized_list = 1")
has_itemized = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM itemized_details")
details_count = cursor.fetchone()[0]

print(f"\n验证后:")
print(f"  has_itemized_list=1: {has_itemized}")
print(f"  分项明细记录数：{details_count}")

conn.close()
