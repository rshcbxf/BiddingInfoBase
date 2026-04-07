"""
文件扫描模块 - 扫描指定文件夹中的投标文件
功能：递归扫描、可中断、支持增量扫描
"""
import os
import threading
import time
from typing import Callable, Optional, Set, Tuple
from dataclasses import dataclass
from pathlib import Path

from .database import Database, BiddingProject
from .parser import DocumentParser


@dataclass
class ScanProgress:
    """扫描进度信息"""
    total_files: int = 0
    processed_files: int = 0
    new_files: int = 0
    updated_files: int = 0
    skipped_files: int = 0
    error_files: int = 0
    current_file: str = ""
    is_running: bool = False
    is_finished: bool = False


class FileScanner:
    """文件扫描器"""

    SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx'}

    def __init__(self, db: Database, parser: DocumentParser):
        self.db = db
        self.parser = parser
        self._stop_event = threading.Event()
        self._progress = ScanProgress()
        self._lock = threading.Lock()

    @property
    def progress(self) -> ScanProgress:
        """获取当前扫描进度"""
        with self._lock:
            return self._progress

    def _update_progress(self, **kwargs):
        """线程安全地更新进度"""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._progress, key):
                    setattr(self._progress, key, value)

    def stop(self):
        """停止扫描"""
        self._stop_event.set()
        self._update_progress(is_running=False)

    def is_stopped(self) -> bool:
        """检查是否被停止"""
        return self._stop_event.is_set()

    def reset(self):
        """重置扫描器状态"""
        self._stop_event.clear()
        self._update_progress(
            total_files=0,
            processed_files=0,
            new_files=0,
            updated_files=0,
            skipped_files=0,
            error_files=0,
            current_file="",
            is_running=False,
            is_finished=False,
        )

    def scan(self, folder_path: str,
             only_new: bool = False,
             rescan_modified: bool = False,
             on_progress: Optional[Callable[[ScanProgress], None]] = None,
             on_log: Optional[Callable[[str], None]] = None) -> Tuple[int, int]:
        """
        扫描文件夹

        参数:
            folder_path: 要扫描的文件夹路径
            only_new: 仅扫描新文件（跳过已扫描且未修改的文件）
            rescan_modified: 重新解析已修改的文件
            on_progress: 进度回调函数
            on_log: 日志回调函数

        返回:
            (成功处理的文件数，跳过或错误的文件数)
        """
        self.reset()
        self._stop_event.clear()

        if not os.path.isdir(folder_path):
            if on_log:
                on_log(f"[ERROR] 无效的文件夹路径：{folder_path}")
            return 0, 0

        # 收集所有待处理的文件
        self._update_progress(is_running=True)
        if on_log:
            on_log(f"[INFO] 开始扫描文件夹：{folder_path}")

        files_to_process = self._collect_files(folder_path)
        total = len(files_to_process)
        self._update_progress(total_files=total)

        if total == 0:
            if on_log:
                on_log("[INFO] 未找到支持的文档文件 (.pdf/.doc/.docx)")
            self._update_progress(is_running=False, is_finished=True)
            return 0, 0

        if on_log:
            on_log(f"[INFO] 找到 {total} 个文件待处理")

        success_count = 0
        skip_count = 0

        valid_paths: Set[str] = set()

        # 处理每个文件
        for i, file_path in enumerate(files_to_process):
            # 检查是否被停止
            if self.is_stopped():
                if on_log:
                    on_log("[INFO] 用户中断扫描")
                break

            self._update_progress(current_file=file_path)

            # 发送进度回调
            if on_progress:
                on_progress(self.progress)

            valid_paths.add(file_path)

            # 检查是否需要扫描
            try:
                stat = os.stat(file_path)
                file_hash = self.db.calculate_file_hash(file_path)
                modified_time = stat.st_mtime
                file_size = stat.st_size
            except Exception as e:
                self._update_progress(error_files=self.progress.error_files + 1)
                if on_log:
                    on_log(f"[ERROR] 无法读取文件：{file_path} - {e}")
                skip_count += 1
                continue

            # 检查是否需要重新扫描
            existing = self.db.get_file_record(file_path)

            should_scan = True
            if existing:
                is_modified = (existing['file_hash'] != file_hash or
                               existing['modified_time'] != modified_time)

                if is_modified and rescan_modified:
                    if on_log:
                        on_log(f"[UPDATE] 文件已修改，重新解析：{os.path.basename(file_path)}")
                elif only_new and not is_modified:
                    # 仅扫描新文件，且文件未修改
                    should_scan = False
                    self._update_progress(
                        skipped_files=self.progress.skipped_files + 1)
                    if on_log:
                        on_log(f"[SKIP] 跳过已扫描：{os.path.basename(file_path)}")
                    skip_count += 1
                elif not only_new and not rescan_modified:
                    # 全量扫描但不重新解析已修改文件
                    should_scan = False
                    self._update_progress(
                        skipped_files=self.progress.skipped_files + 1)
                    skip_count += 1

            if not should_scan:
                continue

            # 解析文件
            try:
                if on_log:
                    on_log(f"[PARSE] 正在解析：{os.path.basename(file_path)}")

                parsed = self.parser.parse_file(file_path)

                # 过滤非投标文件
                if not self.parser.is_bid_document(file_path, parsed.raw_text):
                    if on_log:
                        on_log(f"[SKIP] 非投标文件，跳过：{os.path.basename(file_path)}")
                    self._update_progress(
                        skipped_files=self.progress.skipped_files + 1,
                        processed_files=self.progress.processed_files + 1)
                    continue

                # 检查是否存在同一项目的其他版本（项目名称 + 投标单位 + 开标日期 相同）
                # 如果存在，只保留修改时间最晚的版本
                existing_project = None
                if parsed.project_name and parsed.bidder_org and parsed.bid_date:
                    existing_project = self.db.get_project_by_composite_key(
                        parsed.project_name, parsed.bidder_org, parsed.bid_date)

                # 如果已存在同一项目的记录，且当前文件修改时间更早，则跳过
                if existing_project:
                    if modified_time <= existing_project['modified_time']:
                        if on_log:
                            on_log(f"[SKIP] 发现更新版本，跳过当前文件：{os.path.basename(file_path)}")
                        self._update_progress(
                            skipped_files=self.progress.skipped_files + 1,
                            processed_files=self.progress.processed_files + 1)
                        continue
                    else:
                        # 当前文件更新，删除旧记录
                        if on_log:
                            on_log(f"[REPLACE] 发现更新版本，删除旧记录：{os.path.basename(file_path)}")
                        self.db.delete_by_id(existing_project['id'])

                # 保存到数据库
                project = BiddingProject(
                    id=None,
                    file_path=file_path,
                    file_hash=file_hash,
                    file_size=file_size,
                    modified_time=modified_time,
                    scan_time=time.time(),
                    project_name=parsed.project_name,
                    bid_date=parsed.bid_date,
                    tender_org=parsed.tender_org,
                    bidder_org=parsed.bidder_org,
                    has_itemized_list=parsed.has_itemized_list,
                )

                self.db.insert_or_update(project)

                # 获取项目 ID，保存分项明细数据
                project_record = self.db.get_project_by_file_path(file_path)
                if project_record and parsed.itemized_details:
                    # 转换为数据库的 ItemizedDetail 类型
                    from .database import ItemizedDetail as DbItemizedDetail
                    db_details = []
                    for detail in parsed.itemized_details:
                        db_details.append(DbItemizedDetail(
                            id=None,
                            project_id=project_record['id'],
                            device_name=detail.device_name,
                            brand=detail.brand,
                            model=detail.model,
                            quantity=detail.quantity,
                            tax_rate=detail.tax_rate,
                            unit_price_tax_included=detail.unit_price_tax_included,
                            unit_price_tax_excluded=detail.unit_price_tax_excluded,
                        ))
                    self.db.insert_itemized_details(project_record['id'], db_details)
                    if on_log:
                        on_log(f"[DETAILS] 已保存 {len(parsed.itemized_details)} 条分项明细")

                if existing:
                    self._update_progress(
                        updated_files=self.progress.updated_files + 1)
                    if on_log:
                        on_log(f"[SUCCESS] 已更新：{parsed.project_name or os.path.basename(file_path)}")
                else:
                    self._update_progress(
                        new_files=self.progress.new_files + 1)
                    if on_log:
                        on_log(f"[SUCCESS] 已添加：{parsed.project_name or os.path.basename(file_path)}")

                success_count += 1

            except Exception as e:
                self._update_progress(
                    error_files=self.progress.error_files + 1)
                if on_log:
                    on_log(f"[ERROR] 解析失败：{os.path.basename(file_path)} - {e}")
                skip_count += 1

            self._update_progress(processed_files=self.progress.processed_files + 1)

        # 扫描完成
        self._update_progress(
            is_running=False,
            is_finished=True,
            current_file="",
        )

        if on_progress:
            on_progress(self.progress)

        if on_log:
            if self.is_stopped():
                on_log(f"[INFO] 扫描中断：成功 {success_count}, 跳过/错误 {skip_count}")
            else:
                on_log(f"[INFO] 扫描完成：成功 {success_count}, 跳过/错误 {skip_count}")

        return success_count, skip_count

    def _collect_files(self, folder_path: str) -> list:
        """递归收集所有支持的文件"""
        files = []
        for root, dirs, filenames in os.walk(folder_path):
            # 跳过隐藏文件夹
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    files.append(os.path.join(root, filename))

        return files

    def delete_invalid_records(self, on_log: Optional[Callable[[str], None]] = None) -> int:
        """删除文件已不存在的记录"""
        if on_log:
            on_log("[INFO] 正在检查无效记录...")

        # 获取所有记录
        all_records = self.db.get_all_records()
        invalid_count = 0

        for record in all_records:
            if not os.path.exists(record['file_path']):
                self.db.delete_by_id(record['id'])
                invalid_count += 1
                if on_log:
                    on_log(f"[DELETE] 删除无效记录：{record['file_path']}")

        if on_log:
            if invalid_count > 0:
                on_log(f"[INFO] 已删除 {invalid_count} 条无效记录")
            else:
                on_log("[INFO] 没有无效记录")

        return invalid_count
