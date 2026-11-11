# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, r'C:\Projects\BiddingInfoBase')

from bidding_gui.parser import DocumentParser
import re

file_path = r"C:\Projects\BiddingInfoBase\sample_doc\2026 年工作相关\260120 什邡 EPS 第三次\投标文件.docx"

print(f"文件路径：{file_path}")
print(f"文件存在：{os.path.exists(file_path)}")

if os.path.exists(file_path):
    print(f"文件大小：{os.path.getsize(file_path) / 1024 / 1024:.2f} MB")

    parser = DocumentParser()
    text = parser._parse_doc(file_path)

    print(f"\n文件内容长度：{len(text)}")
    print(f"\n文件内容前 3000 字符：")
    print(text[:3000])

    # 检查是否为投标文件
    filename = os.path.basename(file_path).lower()
    exclude_keywords = ['封套', '封面', '标书封面', '投标函封面', '目录', '封底', '备忘', '备注', '注意事项', '招标', '格式', '模板', '样表', '样张', '关键点', '答疑', '澄清']

    print("\n=== 文件名排除检查 ===")
    for kw in exclude_keywords:
        if kw in filename:
            print(f"匹配排除词：'{kw}'")
            break
    else:
        print("没有匹配排除词，通过检查")

    # 检查实质性内容
    substantive_patterns = [
        (r'(?:^|\n)\s*(?:第.+?[章编部节]|[(][^)）]+[)）]|\d+\.|\d+|[一二三四五六七八九十]+[、.])\s*投标函', '投标函'),
        (r'(?:^|\n)\s*(?:第.+?[章编部节]|[(][^)）]+[)）]|\d+\.|\d+|[一二三四五六七八九十]+[、.])\s*开标一览表', '开标一览表'),
        (r'(?:^|\n)\s*(?:第.+?[章编部节]|[(][^)）]+[)）]|\d+\.|\d+|[一二三四五六七八九十]+[、.])\s*营业执照', '营业执照'),
    ]

    print("\n=== 实质性内容检查 ===")
    matched = None
    for pattern, name in substantive_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        print(f"{name}: {'找到' if match else '未找到'}")
        if match:
            matched = name
            print(f"  匹配内容：{repr(match.group()[:100])}")

    # 运行完整的 is_bid_document 检查
    result = parser.is_bid_document(file_path, text)
    print(f"\nis_bid_document 结果：{result}")

    if not result and matched:
        print(f"\n=== 验证{matched}内容 ===")
        bid_date = parser._extract_bid_date_for_validation(text)
        print(f"提取的日期：{repr(bid_date)}")

        validate_result = parser._validate_bid_letter_or_price_list(text, matched, bid_date)
        print(f"验证结果：{validate_result}")
