"""数据库外键级联与孤儿明细清理的回归测试。"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bidding_gui.database import BiddingProject, Database, ItemizedDetail


def _project(file_name: str) -> BiddingProject:
    return BiddingProject(
        id=None,
        file_path=file_name,
        file_hash="hash",
        file_size=1024,
        modified_time=1.0,
        scan_time=2.0,
        project_name="测试项目",
        bid_date="2026-01-20",
        tender_org="招标单位",
        bidder_org="投标单位",
        has_itemized_list=True,
    )


def _detail(project_id: int) -> ItemizedDetail:
    return ItemizedDetail(
        id=None,
        project_id=project_id,
        device_name="测试设备",
        brand="品牌",
        model="型号",
        quantity="1",
        tax_rate="",
        unit_price_tax_included="",
        unit_price_tax_excluded="",
    )


def test_foreign_keys_enabled(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    try:
        assert db.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        db.close()


def test_delete_by_id_cascades_itemized_details(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    try:
        db.insert_or_update(_project("a.docx"))
        project_id = db.get_project_by_file_path("a.docx")["id"]
        db.insert_itemized_details(project_id, [_detail(project_id)])
        assert len(db.get_itemized_details(project_id)) == 1

        db.delete_by_id(project_id)
        assert db.get_itemized_details(project_id) == []
    finally:
        db.close()


def test_orphan_details_cleaned_on_open(tmp_path):
    db_path = str(tmp_path / "test.db")
    db = Database(db_path)
    db.insert_or_update(_project("b.docx"))
    project_id = db.get_project_by_file_path("b.docx")["id"]
    db.insert_itemized_details(project_id, [_detail(project_id)])
    db.close()

    # 绕过外键直接删除主记录，制造孤儿明细
    raw = sqlite3.connect(db_path)
    raw.execute("DELETE FROM bidding_projects WHERE id = ?", (project_id,))
    raw.commit()
    raw.close()

    reopened = Database(db_path)  # 打开时应自动清理孤儿明细
    try:
        assert reopened.get_itemized_details(project_id) == []
    finally:
        reopened.close()
