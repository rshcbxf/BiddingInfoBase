"""
GUI 主窗口 - 投标文件信息管理系统界面
功能：数据库配置、文件扫描、查询显示、导出结果
"""
import os
import csv
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from typing import Optional, List, Dict

import customtkinter as ctk

from .database import Database
from .parser import DocumentParser
from .scanner import FileScanner, ScanProgress


# 设置外观
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    """投标文件信息管理系统主窗口"""

    def __init__(self, db_path: Optional[str] = None):
        super().__init__()

        self.title("投标文件信息管理系统")
        self.geometry("1200x800")
        self.minsize(1000, 700)

        # 初始化组件
        self.db: Optional[Database] = None
        self.parser = DocumentParser()
        self.scanner: Optional[FileScanner] = None
        self.scan_thread: Optional[threading.Thread] = None

        # 数据库路径优先级：显式参数 > 环境变量 BIDDING_DB_PATH > 用户主目录默认路径
        self.db_path = self._resolve_db_path(db_path)

        self._setup_ui()
        self._init_database()

    @staticmethod
    def _resolve_db_path(db_path: Optional[str] = None) -> str:
        """解析数据库文件路径。

        优先级：显式参数 > 环境变量 ``BIDDING_DB_PATH`` > 用户主目录 ``bidding_info.db``。
        """
        candidate = db_path or os.environ.get("BIDDING_DB_PATH")
        if candidate:
            return os.path.abspath(os.path.expanduser(candidate))
        return os.path.join(os.path.expanduser("~"), "bidding_info.db")

    def _setup_ui(self):
        """设置用户界面"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # ===== 1. 数据库配置区域 =====
        self.db_frame = ctk.CTkFrame(self)
        self.db_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(self.db_frame, text="数据库配置:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w")

        self.db_path_entry = ctk.CTkEntry(self.db_frame, width=600)
        self.db_path_entry.insert(0, self.db_path)
        self.db_path_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.db_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            self.db_frame, text="浏览", command=self._browse_db,
            width=60
        ).grid(row=0, column=2, padx=5, pady=5)

        ctk.CTkButton(
            self.db_frame, text="重建", command=self._reinit_db,
            width=60, fg_color="orange"
        ).grid(row=0, column=3, padx=5, pady=5)

        # 统计信息
        self.stats_label = ctk.CTkLabel(
            self.db_frame, text="记录：0 | 投标单位：0 | 招标单位：0",
            text_color="gray"
        )
        self.stats_label.grid(row=0, column=4, padx=20, pady=5)

        # ===== 2. 扫描控制区域 =====
        self.scan_frame = ctk.CTkFrame(self)
        self.scan_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(self.scan_frame, text="扫描控制:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w")

        self.scan_path_entry = ctk.CTkEntry(self.scan_frame, width=600)
        self.scan_path_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.scan_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            self.scan_frame, text="浏览", command=self._browse_folder,
            width=60
        ).grid(row=0, column=2, padx=5, pady=5)

        # 扫描选项
        self.only_new_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            self.scan_frame, text="仅扫描新文件",
            variable=self.only_new_var
        ).grid(row=1, column=0, padx=5, pady=2, sticky="w")

        self.rescan_modified_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self.scan_frame, text="重新解析已修改文件",
            variable=self.rescan_modified_var
        ).grid(row=1, column=1, padx=5, pady=2, sticky="w")

        # 扫描按钮和进度
        self.btn_frame = ctk.CTkFrame(self.scan_frame)
        self.btn_frame.grid(row=2, column=0, columnspan=5, padx=5, pady=5, sticky="ew")

        self.start_scan_btn = ctk.CTkButton(
            self.btn_frame, text="开始扫描", command=self._start_scan,
            width=100
        )
        self.start_scan_btn.pack(side="left", padx=5)

        self.stop_scan_btn = ctk.CTkButton(
            self.btn_frame, text="停止", command=self._stop_scan,
            width=60, fg_color="orange", state="disabled"
        )
        self.stop_scan_btn.pack(side="left", padx=5)

        self.clear_invalid_btn = ctk.CTkButton(
            self.btn_frame, text="清除无效记录",
            command=self._clear_invalid_records,
            width=100, fg_color="gray"
        )
        self.clear_invalid_btn.pack(side="left", padx=5)

        self.progress_label = ctk.CTkLabel(
            self.btn_frame, text="进度：0 / 0", width=150
        )
        self.progress_label.pack(side="right", padx=5)

        self.status_label = ctk.CTkLabel(
            self.btn_frame, text="就绪", text_color="gray"
        )
        self.status_label.pack(side="right", padx=10)

        # ===== 3. 查询区域 =====
        self.query_frame = ctk.CTkFrame(self)
        self.query_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(self.query_frame, text="查询条件:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(self.query_frame, text="投标单位:").grid(
            row=0, column=1, padx=5, pady=5, sticky="e")
        self.bidder_entry = ctk.CTkEntry(self.query_frame, width=200)
        self.bidder_entry.grid(row=0, column=2, padx=5, pady=5)

        ctk.CTkLabel(self.query_frame, text="分项明细:").grid(
            row=0, column=3, padx=5, pady=5, sticky="e")
        self.itemized_var = ctk.StringVar(value="")
        self.itemized_combo = ctk.CTkComboBox(
            self.query_frame, values=["", "是", "否"],
            variable=self.itemized_var, width=100
        )
        self.itemized_combo.grid(row=0, column=4, padx=5, pady=5)

        ctk.CTkLabel(self.query_frame, text="投标函日期:").grid(
            row=1, column=1, padx=5, pady=5, sticky="e")
        self.date_start_entry = ctk.CTkEntry(self.query_frame, width=100, placeholder_text="YYYY-MM-DD")
        self.date_start_entry.grid(row=1, column=2, padx=5, pady=5)

        ctk.CTkLabel(self.query_frame, text="至").grid(
            row=1, column=3, padx=5, pady=5, sticky="e")
        self.date_end_entry = ctk.CTkEntry(self.query_frame, width=100, placeholder_text="YYYY-MM-DD")
        self.date_end_entry.grid(row=1, column=4, padx=5, pady=5)

        # 查询按钮
        self.query_btn_frame = ctk.CTkFrame(self.query_frame)
        self.query_btn_frame.grid(row=2, column=0, columnspan=5, padx=5, pady=5)

        ctk.CTkButton(
            self.query_btn_frame, text="查询", command=self._search,
            width=80
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            self.query_btn_frame, text="清空条件",
            command=self._clear_query, width=80, fg_color="gray"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            self.query_btn_frame, text="显示全部",
            command=self._show_all, width=80
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            self.query_btn_frame, text="导出 CSV",
            command=self._export_csv, width=80, fg_color="green"
        ).pack(side="left", padx=5)

        self.result_count_label = ctk.CTkLabel(
            self.query_btn_frame, text="共 0 条记录", text_color="gray"
        )
        self.result_count_label.pack(side="right", padx=10)

        # ===== 4. 结果显示区域 =====
        self.result_frame = ctk.CTkFrame(self)
        self.result_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)
        self.grid_rowconfigure(3, weight=1)

        # 表格
        columns = (
            "id", "project_name", "bid_date", "tender_org",
            "bidder_org", "has_itemized_list", "file_path", "scan_time"
        )

        self.tree = ttk.Treeview(
            self.result_frame, columns=columns, show="headings",
            selectmode="extended"
        )

        # 设置列标题
        self.tree.heading("id", text="ID")
        self.tree.heading("project_name", text="项目名称")
        self.tree.heading("bid_date", text="投标函日期")
        self.tree.heading("tender_org", text="招标单位")
        self.tree.heading("bidder_org", text="投标单位")
        self.tree.heading("has_itemized_list", text="分项明细")
        self.tree.heading("file_path", text="文件路径")
        self.tree.heading("scan_time", text="扫描时间")

        # 设置列宽
        self.tree.column("id", width=50)
        self.tree.column("project_name", width=200)
        self.tree.column("bid_date", width=100)
        self.tree.column("tender_org", width=150)
        self.tree.column("bidder_org", width=150)
        self.tree.column("has_itemized_list", width=80)
        self.tree.column("file_path", width=300)
        self.tree.column("scan_time", width=150)

        # 滚动条 - 垂直和水平
        v_scrollbar = ttk.Scrollbar(
            self.result_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(
            self.result_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")

        # 绑定右键菜单
        self.tree.bind("<Button-3>", self._show_context_menu)

        # ===== 5. 操作按钮区域（窗体下方） =====
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkButton(
            self.action_frame, text="删除选中",
            command=self._delete_selected, width=100,
            fg_color="red"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            self.action_frame, text="查看详情",
            command=self._show_detail, width=100
        ).pack(side="left", padx=5)

        # ===== 6. 日志区域 =====
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid(row=5, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(self.log_frame, text="日志输出:").grid(
            row=0, column=0, padx=5, pady=2, sticky="w")

        ctk.CTkButton(
            self.log_frame, text="清空", command=self._clear_log,
            width=60, height=20
        ).grid(row=0, column=1, padx=5, pady=2)

        ctk.CTkButton(
            self.log_frame, text="保存", command=self._save_log,
            width=60, height=20
        ).grid(row=0, column=2, padx=5, pady=2)

        self.log_text = ctk.CTkTextbox(
            self.log_frame, height=100, state="disabled"
        )
        self.log_text.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        self.log_frame.grid_columnconfigure(0, weight=1)

    def _init_database(self):
        """初始化数据库"""
        try:
            if self.db:
                self.db.close()
            parent_dir = os.path.dirname(self.db_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            self.db = Database(self.db_path)
            self._update_stats()
            self._log(f"[INFO] 数据库已打开：{self.db_path}")
        except Exception as e:
            messagebox.showerror("数据库错误", f"无法打开数据库:\n{e}")

    def _browse_db(self):
        """选择数据库文件"""
        path = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite 数据库", "*.db"), ("所有文件", "*.*")],
            title="选择数据库文件"
        )
        if path:
            self.db_path_entry.delete(0, "end")
            self.db_path_entry.insert(0, path)
            self.db_path = path
            self._init_database()

    def _reinit_db(self):
        """重建数据库"""
        if messagebox.askyesno("确认", "确定要重建数据库吗？\n现有数据将被清空！"):
            if self.db:
                self.db.close()
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            self.db = Database(self.db_path)
            self._update_stats()
            self._log("[INFO] 数据库已重建")

    def _browse_folder(self):
        """选择扫描文件夹"""
        folder = filedialog.askdirectory(
            title="选择要扫描的文件夹"
        )
        if folder:
            self.scan_path_entry.delete(0, "end")
            self.scan_path_entry.insert(0, folder)

    def _start_scan(self):
        """开始扫描"""
        folder_path = self.scan_path_entry.get().strip()
        if not folder_path:
            messagebox.showwarning("警告", "请先选择要扫描的文件夹")
            return

        if not os.path.isdir(folder_path):
            messagebox.showerror("错误", f"无效的文件夹路径:\n{folder_path}")
            return

        if not self.db:
            messagebox.showerror("错误", "数据库未初始化")
            return

        # 更新 UI 状态
        self.start_scan_btn.configure(state="disabled")
        self.stop_scan_btn.configure(state="normal")
        self.scan_path_entry.configure(state="disabled")

        # 创建扫描器
        self.scanner = FileScanner(self.db, self.parser)

        # 在后台线程中执行扫描
        import threading
        self.scan_thread = threading.Thread(
            target=self._run_scan,
            args=(folder_path,),
            daemon=True
        )
        self.scan_thread.start()

    def _run_scan(self, folder_path: str):
        """运行扫描（后台线程）"""
        def on_progress(progress: ScanProgress):
            self.after(0, self._update_scan_progress, progress)

        def on_log(message: str):
            self.after(0, self._log, message)

        success, skip = self.scanner.scan(
            folder_path,
            only_new=self.only_new_var.get(),
            rescan_modified=self.rescan_modified_var.get(),
            on_progress=on_progress,
            on_log=on_log,
        )

        self.after(0, self._scan_complete, success, skip)

    def _update_scan_progress(self, progress: ScanProgress):
        """更新扫描进度"""
        self.progress_label.configure(
            text=f"进度：{progress.processed_files} / {progress.total_files}"
        )
        self.status_label.configure(text=progress.current_file[:50] if progress.current_file else "")

        if progress.is_finished:
            self._update_stats()
            self._show_all()

    def _scan_complete(self, success: int, skip: int):
        """扫描完成"""
        self.start_scan_btn.configure(state="normal")
        self.stop_scan_btn.configure(state="disabled")
        self.scan_path_entry.configure(state="normal")

        self._log(f"[INFO] 扫描结束：成功 {success} 个，跳过/错误 {skip} 个")
        messagebox.showinfo("扫描完成", f"扫描完成!\n成功：{success} 个文件\n跳过/错误：{skip} 个")

    def _stop_scan(self):
        """停止扫描"""
        if self.scanner and self.scanner.progress.is_running:
            self.scanner.stop()
            self._log("[INFO] 正在停止扫描...")

    def _clear_invalid_records(self):
        """清除无效记录"""
        if not self.db:
            return

        if messagebox.askyesno("确认", "确定要清除无效记录吗？\n这将删除所有文件路径不存在的记录。"):
            count = self.scanner.delete_invalid_records(
                on_log=lambda msg: self._log(msg)
            ) if self.scanner else self.db.delete_invalid_records(set())
            self._update_stats()
            self._show_all()
            if count > 0:
                messagebox.showinfo("完成", f"已删除 {count} 条无效记录")
            else:
                messagebox.showinfo("完成", "没有无效记录")

    def _search(self):
        """执行查询"""
        if not self.db:
            return

        bidder = self.bidder_entry.get().strip()
        itemized = self.itemized_var.get().strip()
        date_start = self.date_start_entry.get().strip()
        date_end = self.date_end_entry.get().strip()

        # 转换分项明细选项为布尔值
        has_itemized = None
        if itemized == "是":
            has_itemized = True
        elif itemized == "否":
            has_itemized = False

        results = self.db.search(
            bidder_org=bidder if bidder else None,
            has_itemized_list=has_itemized,
            bid_date_start=date_start if date_start else None,
            bid_date_end=date_end if date_end else None,
        )

        self._populate_tree(results)
        self.result_count_label.configure(text=f"共 {len(results)} 条记录")

    def _clear_query(self):
        """清空查询条件"""
        self.bidder_entry.delete(0, "end")
        self.itemized_var.set("")
        self.date_start_entry.delete(0, "end")
        self.date_end_entry.delete(0, "end")

    def _show_all(self):
        """显示全部记录"""
        if not self.db:
            return

        results = self.db.get_all_records()
        self._populate_tree(results)
        self.result_count_label.configure(text=f"共 {len(results)} 条记录")

    def _populate_tree(self, records: List[Dict]):
        """填充表格"""
        # 清空现有数据
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 插入数据
        for record in records:
            scan_time = datetime.fromtimestamp(record['scan_time']).strftime('%Y-%m-%d %H:%M')
            has_itemized = "是" if record.get('has_itemized_list') else "否"
            self.tree.insert("", "end", values=(
                record['id'],
                record['project_name'] or "",
                record['bid_date'] or "",
                record['tender_org'] or "",
                record['bidder_org'] or "",
                has_itemized,
                record['file_path'] or "",
                scan_time,
            ))

    def _update_stats(self):
        """更新统计信息"""
        if not self.db:
            return

        stats = self.db.get_statistics()
        self.stats_label.configure(
            text=f"记录：{stats['total_records']} | "
                 f"投标单位：{stats['unique_bidders']} | "
                 f"招标单位：{stats['unique_tenders']}"
        )

    def _export_csv(self):
        """导出为 CSV"""
        selected = self.tree.selection()

        if not selected:
            # 导出全部
            items = self.tree.get_children()
            if not items:
                messagebox.showinfo("提示", "没有可导出的数据")
                return

            records = [self.tree.item(item)['values'] for item in items]
        else:
            # 导出选中
            records = [self.tree.item(item)['values'] for item in selected]

        # 选择保存路径
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")],
            title="保存 CSV 文件"
        )

        if not path:
            return

        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "ID", "项目名称", "投标函日期", "招标单位",
                    "投标单位", "分项明细", "文件路径", "扫描时间"
                ])
                writer.writerows(records)

            self._log(f"[INFO] 已导出 {len(records)} 条记录到：{path}")
            messagebox.showinfo("导出完成", f"已导出 {len(records)} 条记录")
        except Exception as e:
            messagebox.showerror("导出失败", f"无法导出文件:\n{e}")

    def _show_context_menu(self, event):
        """显示右键菜单"""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="查看详情", command=self._show_detail)
        menu.add_command(label="删除记录", command=self._delete_selected)
        menu.add_separator()
        menu.add_command(label="导出选中", command=self._export_csv)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _show_detail(self):
        """显示详情"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择一条记录")
            return

        item = self.tree.item(selected[0])
        values = item['values']
        record_id = values[0]

        detail_win = ctk.CTkToplevel(self)
        detail_win.title("记录详情")
        detail_win.geometry("700x700")

        # 基本信息
        fields = [
            ("ID", values[0]),
            ("项目名称", values[1]),
            ("投标函日期", values[2]),
            ("招标单位", values[3]),
            ("投标单位", values[4]),
            ("分项明细", values[5]),
            ("文件路径", values[6]),
            ("扫描时间", values[7]),
        ]

        for i, (label, value) in enumerate(fields):
            ctk.CTkLabel(detail_win, text=f"{label}:", font=("bold", 12)).grid(
                row=i, column=0, padx=10, pady=10, sticky="w")

            text_widget = ctk.CTkTextbox(detail_win, height=30, width=450)
            text_widget.insert("0.0", str(value))
            text_widget.configure(state="disabled")
            text_widget.grid(row=i, column=1, padx=10, pady=10, sticky="ew")

        # 分项明细表格
        if self.db:
            details = self.db.get_itemized_details(record_id)
            if details:
                label_row = len(fields)
                table_row = len(fields) + 1

                ctk.CTkLabel(detail_win, text="分项明细列表:", font=("bold", 14)).grid(
                    row=label_row, column=0, columnspan=2, padx=10, pady=(20, 10), sticky="w")

                # 创建表格框架
                table_frame = ctk.CTkFrame(detail_win)
                table_frame.grid(row=table_row, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

                # 配置窗口行列权重，确保表格可以展开
                detail_win.grid_rowconfigure(table_row, weight=1)
                detail_win.grid_columnconfigure(0, weight=1)
                detail_win.grid_columnconfigure(1, weight=1)

                # 定义列
                columns = ("device_name", "brand", "model", "quantity", "tax_rate",
                           "unit_price_tax_included", "unit_price_tax_excluded")
                column_names = ["设备名称", "品牌", "型号", "数量", "税率", "含税单价", "不含税单价"]

                # 创建 Treeview 和滚动条
                v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical")
                h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal")
                detail_tree = ttk.Treeview(
                    table_frame, columns=columns, show="headings", height=10,
                    yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set
                )

                v_scrollbar.config(command=detail_tree.yview)
                h_scrollbar.config(command=detail_tree.xview)

                # 设置列标题
                for col, name in zip(columns, column_names):
                    detail_tree.heading(col, text=name)
                    detail_tree.column(col, width=120)

                # 填充数据
                for detail in details:
                    detail_tree.insert("", "end", values=(
                        detail.get('device_name', ''),
                        detail.get('brand', ''),
                        detail.get('model', ''),
                        detail.get('quantity', ''),
                        detail.get('tax_rate', ''),
                        detail.get('unit_price_tax_included', ''),
                        detail.get('unit_price_tax_excluded', ''),
                    ))

                # 布局表格和滚动条
                detail_tree.grid(row=0, column=0, sticky="nsew")
                v_scrollbar.grid(row=0, column=1, sticky="ns")
                h_scrollbar.grid(row=1, column=0, sticky="ew")
                table_frame.grid_rowconfigure(0, weight=1)
                table_frame.grid_columnconfigure(0, weight=1)

        detail_win.grid_columnconfigure(1, weight=1)

    def _delete_selected(self):
        """删除选中记录"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择要删除的记录")
            return

        count = len(selected)
        if messagebox.askyesno("确认", f"确定要删除选中的 {count} 条记录吗？"):
            for item in selected:
                values = self.tree.item(item)['values']
                if self.db:
                    self.db.delete_by_id(values[0])
                self.tree.delete(item)

            self._update_stats()
            self._log(f"[INFO] 已删除 {count} 条记录")
            messagebox.showinfo("完成", f"已删除 {count} 条记录")

    def _log(self, message: str):
        """添加日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        self.log_text.configure(state="normal")
        self.log_text.insert("end", log_entry)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        """清空日志"""
        self.log_text.configure(state="normal")
        self.log_text.delete("0.0", "end")
        self.log_text.configure(state="disabled")

    def _save_log(self):
        """保存日志"""
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            title="保存日志文件"
        )

        if not path:
            return

        try:
            content = self.log_text.get("0.0", "end")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            self._log(f"[INFO] 日志已保存：{path}")
        except Exception as e:
            messagebox.showerror("保存失败", f"无法保存日志:\n{e}")

    def on_closing(self):
        """窗口关闭时的处理"""
        if self.scanner and self.scanner.progress.is_running:
            if messagebox.askyesno("警告", "扫描正在进行中，确定要退出吗？"):
                self.scanner.stop()
            else:
                return

        if self.db:
            self.db.close()
        self.destroy()
