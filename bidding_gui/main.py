"""
投标文件信息管理系统 - 程序入口
"""
import sys
import os

# 添加父目录到路径，确保导入正确
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bidding_gui.app import App


def main():
    """主函数"""
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
