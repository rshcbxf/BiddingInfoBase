# -*- coding: utf-8 -*-
"""测试分项明细提取"""
import sys
sys.path.insert(0, r'C:\Projects\BiddingInfoBase')

from bidding_gui.parser import DocumentParser

# 测试用例 1: 有分项明细表格的文本
test_text_1 = """
第七章 分项报价表

序号  设备名称  品牌  型号  数量  税率  含税单价
1   智能空调  格力  KFR-35GW  10  13%  5000
2   路由器  华为  AX3  5  13%  300
"""

# 测试用例 2: 没有序号列的分项明细表格
test_text_2 = """
分项报价明细表

设备名称  品牌  型号  数量  含税单价
智能空调  格力  KFR-35GW  10  5000
路由器  华为  AX3  5  300
"""

# 测试用例 3: 总价表（应该被排除）
test_text_3 = """
报价汇总表

项目名称  总价  含税总价
智能空调项目  50000  56500
"""

# 测试用例 4: 在分项章节内的表格
test_text_4 = """
第五章 分项报价表

5.1 设备清单

序号  名称  品牌  型号  数量
1   空调  格力  KFR-35GW  10

5.2 分项报价明细

设备名称  品牌  型号  数量  含税单价
智能空调  格力  KFR-35GW  10  5000
"""

parser = DocumentParser()

print("=== 测试用例 1: 标准分项表格（有序号） ===")
details = parser._extract_itemized_details(test_text_1)
print(f"提取到 {len(details)} 条明细")
for d in details:
    print(f"  {d.device_name} | {d.brand} | {d.model} | {d.quantity}")

print("\n=== 测试用例 2: 没有序号列的分项表格 ===")
details = parser._extract_itemized_details(test_text_2)
print(f"提取到 {len(details)} 条明细")
for d in details:
    print(f"  {d.device_name} | {d.brand} | {d.model} | {d.quantity}")

print("\n=== 测试用例 3: 总价表（应该被排除） ===")
details = parser._extract_itemized_details(test_text_3)
print(f"提取到 {len(details)} 条明细（应该为 0）")

print("\n=== 测试用例 4: 分项章节内的表格 ===")
details = parser._extract_itemized_details(test_text_4)
print(f"提取到 {len(details)} 条明细")
for d in details:
    print(f"  {d.device_name} | {d.brand} | {d.model} | {d.quantity}")
