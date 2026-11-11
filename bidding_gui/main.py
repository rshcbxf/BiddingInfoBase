"""
投标文件信息管理系统 - 程序入口
"""
import argparse
import os
import sys

# 添加父目录到路径，确保导入正确
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bidding_gui.app import App


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="投标文件信息管理系统")
    parser.add_argument(
        "--db",
        dest="db_path",
        default=None,
        help="SQLite 数据库文件路径（优先于环境变量 BIDDING_DB_PATH；"
             "默认使用用户主目录下的 bidding_info.db）",
    )
    args = parser.parse_args()

    app = App(db_path=args.db_path)
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
