"""parser 关键规则的最小回归测试（不依赖 GUI 显示）。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bidding_gui.parser import DocumentParser, ParsedResult


@pytest.fixture(scope="module")
def parser():
    return DocumentParser()


# ---------------------------------------------------------------- 日期归一

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026年01月20日", "2026-01-20"),
        ("2026年1月2日", "2026-01-02"),
        ("2026 年 01 月 20 日", "2026-01-20"),
        ("2026/1/20", "2026-01-20"),
        ("2026.1.20", "2026-01-20"),
        ("2026-1-2", "2026-01-02"),
    ],
)
def test_normalize_date(parser, raw, expected):
    assert parser._normalize_date(raw) == expected


def test_normalize_date_keeps_unknown_text(parser):
    assert parser._normalize_date("日期待定") == "日期待定"


# ------------------------------------------------------------ 投标文件判定

BID_LETTER_TEXT = """
第一章 投标函
致：某某招标代理有限公司：
我方参加贵方组织的某某项目投标。
投标人：某某科技有限公司
2026 年 01 月 20 日
第二章 开标一览表
"""


def test_is_bid_document_accepts_bid_letter(parser):
    assert parser.is_bid_document("投标文件.docx", BID_LETTER_TEXT) is True


def test_is_bid_document_rejects_tender_filename(parser):
    assert parser.is_bid_document("招标文件副本.docx", BID_LETTER_TEXT) is False


def test_is_bid_document_rejects_plain_document(parser):
    text = "这是一份普通说明书，没有实质性的投标章节。"
    assert parser.is_bid_document("说明书.docx", text) is False


# ---------------------------------------------------------------- 字段抽取

def test_project_name_strips_section_suffix(parser):
    result = ParsedResult()
    parser._extract_info("项目名称：某市智慧平台建设项目（标段二）\n", result)
    assert result.project_name == "某市智慧平台建设项目"


def test_tender_org_from_bid_letter_strips_trailing_colon(parser):
    text = "投标函\n致：某某招标代理有限公司：\n"
    assert parser._extract_tender_from_bid_letter(text) == "某某招标代理有限公司"


# ------------------------------------------------------------ 分项明细提取

def test_extract_itemized_details_basic(parser):
    text = (
        "第七章 分项报价明细表\n"
        "设备名称\t品牌\t型号\t数量\t单位\n"
        "智能空调\t格力\tKFR-35GW\t10\t台\n"
        "路由器\t华为\tAX3\t5\t台\n"
    )
    details = parser._extract_itemized_details(text)
    assert [d.device_name for d in details] == ["智能空调", "路由器"]
    assert details[0].brand == "格力"
    assert details[0].model == "KFR-35GW"
    assert details[0].quantity == "10"


def test_extract_itemized_details_after_chapter_title(parser):
    """章节标题先把 in_itemized_table 置位时仍应返回明细（has_valid_table 回归）。"""
    text = (
        "第五章 分项报价明细表\n"
        "序号\t设备名称\t数量\t单位\n"
        "1\tEPS主机\t1\t台\n"
    )
    assert len(parser._extract_itemized_details(text)) == 1


def test_total_price_table_is_excluded(parser):
    text = (
        "报价汇总表\n"
        "项目名称\t总价\t含税总价\n"
        "某项目\t50000\t56500\n"
    )
    assert parser._extract_itemized_details(text) == []


def test_explanation_rows_are_filtered(parser):
    """授权书模板中的「（制造商名称）是在…」说明行不应被当成设备明细。"""
    text = (
        "分项报价明细表\n"
        "设备名称\t品牌\t型号\t数量\t单位\n"
        "（制造商名称）是在\t中国\t未知\t\t\n"
        "EPS主机\t商宇\tX1\t1\t台\n"
    )
    details = parser._extract_itemized_details(text)
    assert [d.device_name for d in details] == ["EPS主机"]
