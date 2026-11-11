"""数据库路径解析（--db / BIDDING_DB_PATH）的回归测试。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bidding_gui.app import App


def test_resolve_db_path_priority(monkeypatch, tmp_path):
    cli_path = str(tmp_path / "cli.db")
    env_path = str(tmp_path / "env.db")

    monkeypatch.setenv("BIDDING_DB_PATH", env_path)
    assert App._resolve_db_path(cli_path) == cli_path
    assert App._resolve_db_path(None) == env_path

    monkeypatch.delenv("BIDDING_DB_PATH")
    assert App._resolve_db_path(None).endswith("bidding_info.db")
