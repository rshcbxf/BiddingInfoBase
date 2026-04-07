"""
数据库操作模块 - SQLite 数据库管理
功能：数据库初始化、增删改查、去重逻辑
"""
import sqlite3
import hashlib
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class BiddingProject:
    """投标项目数据模型"""
    id: Optional[int]
    file_path: str
    file_hash: str
    file_size: int
    modified_time: float
    scan_time: float
    project_name: str
    bid_date: str  # 投标函日期
    tender_org: str  # 招标单位
    bidder_org: str  # 投标单位
    has_itemized_list: bool  # 是否包含分项/明细章节

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'file_path': self.file_path,
            'file_hash': self.file_hash,
            'file_size': self.file_size,
            'modified_time': self.modified_time,
            'scan_time': self.scan_time,
            'project_name': self.project_name,
            'bid_date': self.bid_date,
            'tender_org': self.tender_org,
            'bidder_org': self.bidder_org,
            'has_itemized_list': self.has_itemized_list,
        }


@dataclass
class ItemizedDetail:
    """分项明细数据模型"""
    id: Optional[int]
    project_id: int  # 关联的投标项目 ID
    device_name: str  # 设备/项目名称
    brand: str  # 品牌
    model: str  # 型号
    quantity: str  # 数量
    tax_rate: str  # 税率
    unit_price_tax_included: str  # 含税单价
    unit_price_tax_excluded: str  # 不含税单价

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'project_id': self.project_id,
            'device_name': self.device_name,
            'brand': self.brand,
            'model': self.model,
            'quantity': self.quantity,
            'tax_rate': self.tax_rate,
            'unit_price_tax_included': self.unit_price_tax_included,
            'unit_price_tax_excluded': self.unit_price_tax_excluded,
        }


class Database:
    """SQLite 数据库操作类"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._init_tables()
        self._migrate()  # 执行数据库迁移

    def _connect(self):
        """建立数据库连接"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def _init_tables(self):
        """初始化数据库表"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bidding_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_hash TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                modified_time REAL NOT NULL,
                scan_time REAL NOT NULL,
                project_name TEXT,
                bid_date TEXT,
                tender_org TEXT,
                bidder_org TEXT,
                has_itemized_list INTEGER  -- BOOLEAN: 1=真，0=假
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS itemized_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                device_name TEXT,
                brand TEXT,
                model TEXT,
                quantity TEXT,
                tax_rate TEXT,
                unit_price_tax_included TEXT,
                unit_price_tax_excluded TEXT,
                FOREIGN KEY (project_id) REFERENCES bidding_projects(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_bidder_org
            ON bidding_projects(bidder_org)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_tender_org
            ON bidding_projects(tender_org)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_bid_date
            ON bidding_projects(bid_date)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_project_id
            ON itemized_details(project_id)
        ''')
        self.conn.commit()

    def _migrate(self):
        """迁移旧版数据库结构"""
        cursor = self.conn.cursor()

        # 检查表结构
        cursor.execute("PRAGMA table_info(bidding_projects)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        # 如果是旧版本，包含 bid_content 字段
        if 'bid_content' in columns and 'has_itemized_list' not in columns:
            print("检测到旧版数据库，开始迁移...")

            # 添加新字段
            cursor.execute('''
                ALTER TABLE bidding_projects
                ADD COLUMN has_itemized_list INTEGER DEFAULT 0
            ''')

            # 迁移数据
            cursor.execute('''
                UPDATE bidding_projects
                SET has_itemized_list = CASE
                    WHEN bid_content LIKE '%分项%' OR bid_content LIKE '%明细%' THEN 1
                    ELSE 0
                END
            ''')

            # SQLite 不支持直接删除列，需要重建表
            cursor.execute('''
                CREATE TABLE bidding_projects_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    file_hash TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    modified_time REAL NOT NULL,
                    scan_time REAL NOT NULL,
                    project_name TEXT,
                    bid_date TEXT,
                    tender_org TEXT,
                    bidder_org TEXT,
                    has_itemized_list INTEGER
                )
            ''')

            cursor.execute('''
                INSERT INTO bidding_projects_new
                (id, file_path, file_hash, file_size, modified_time, scan_time,
                 project_name, bid_date, tender_org, bidder_org, has_itemized_list)
                SELECT
                id, file_path, file_hash, file_size, modified_time, scan_time,
                project_name, bid_date, tender_org, bidder_org, has_itemized_list
                FROM bidding_projects
            ''')

            cursor.execute('DROP TABLE bidding_projects')
            cursor.execute('ALTER TABLE bidding_projects_new RENAME TO bidding_projects')

            # 重建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_bidder_org
                ON bidding_projects(bidder_org)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tender_org
                ON bidding_projects(tender_org)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_bid_date
                ON bidding_projects(bid_date)
            ''')

            self.conn.commit()
            print("数据库迁移完成！")

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def calculate_file_hash(self, file_path: str) -> str:
        """计算文件 MD5 哈希值"""
        hasher = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

    def get_file_record(self, file_path: str) -> Optional[Dict]:
        """获取已扫描的文件记录"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM bidding_projects
            WHERE file_path = ?
        ''', (file_path,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def needs_rescan(self, file_path: str, current_hash: str,
                     modified_time: float) -> bool:
        """
        判断文件是否需要重新扫描
        返回：(是否需要重新扫描，现有记录)
        """
        record = self.get_file_record(file_path)
        if not record:
            return True  # 新文件，需要扫描

        # 检查文件是否被修改过
        if record['file_hash'] != current_hash or \
           record['modified_time'] != modified_time:
            return True  # 文件已修改，需要重新扫描

        return False  # 文件未变化，跳过

    def insert_or_update(self, project: BiddingProject):
        """插入或更新记录"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO bidding_projects
            (file_path, file_hash, file_size, modified_time, scan_time,
             project_name, bid_date, tender_org, bidder_org, has_itemized_list)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                file_hash = excluded.file_hash,
                file_size = excluded.file_size,
                modified_time = excluded.modified_time,
                scan_time = excluded.scan_time,
                project_name = excluded.project_name,
                bid_date = excluded.bid_date,
                tender_org = excluded.tender_org,
                bidder_org = excluded.bidder_org,
                has_itemized_list = excluded.has_itemized_list
        ''', (
            project.file_path,
            project.file_hash,
            project.file_size,
            project.modified_time,
            project.scan_time,
            project.project_name,
            project.bid_date,
            project.tender_org,
            project.bidder_org,
            project.has_itemized_list,
        ))
        self.conn.commit()

    def get_project_by_file_path(self, file_path: str) -> Optional[Dict]:
        """根据文件路径获取项目记录"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM bidding_projects
            WHERE file_path = ?
        ''', (file_path,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_project_by_composite_key(self, project_name: str, bidder_org: str, bid_date: str) -> Optional[Dict]:
        """
        根据项目名称 + 投标单位 + 开标日期查询记录
        用于判断是否为同一投标项目的不同版本
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM bidding_projects
            WHERE project_name = ? AND bidder_org = ? AND bid_date = ?
        ''', (project_name, bidder_org, bid_date))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def insert_itemized_details(self, project_id: int, details: List[ItemizedDetail]):
        """批量插入分项明细数据"""
        cursor = self.conn.cursor()
        # 先删除该项目原有的分项明细
        cursor.execute('DELETE FROM itemized_details WHERE project_id = ?', (project_id,))
        # 插入新的分项明细
        for detail in details:
            cursor.execute('''
                INSERT INTO itemized_details
                (project_id, device_name, brand, model, quantity,
                 tax_rate, unit_price_tax_included, unit_price_tax_excluded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id,
                detail.device_name,
                detail.brand,
                detail.model,
                detail.quantity,
                detail.tax_rate,
                detail.unit_price_tax_included,
                detail.unit_price_tax_excluded,
            ))
        self.conn.commit()

    def get_itemized_details(self, project_id: int) -> List[Dict]:
        """获取指定项目的分项明细数据"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM itemized_details
            WHERE project_id = ?
        ''', (project_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def delete_itemized_details_by_project(self, project_id: int):
        """删除指定项目的分项明细数据"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM itemized_details WHERE project_id = ?', (project_id,))
        self.conn.commit()

    def delete_by_id(self, record_id: int):
        """根据 ID 删除记录"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM bidding_projects WHERE id = ?', (record_id,))
        self.conn.commit()

    def delete_by_ids(self, record_ids: List[int]):
        """批量删除记录"""
        cursor = self.conn.cursor()
        placeholders = ','.join('?' * len(record_ids))
        cursor.execute(
            f'DELETE FROM bidding_projects WHERE id IN ({placeholders})',
            record_ids
        )
        self.conn.commit()

    def delete_invalid_records(self, valid_paths: set) -> int:
        """删除文件已不存在的有效记录"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, file_path FROM bidding_projects')
        rows = cursor.fetchall()

        deleted_count = 0
        for row in rows:
            if row['file_path'] not in valid_paths:
                if not os.path.exists(row['file_path']):
                    cursor.execute('DELETE FROM bidding_projects WHERE id = ?',
                                   (row['id'],))
                    deleted_count += 1
        self.conn.commit()
        return deleted_count

    def search(self, bidder_org: str = None, tender_org: str = None,
               has_itemized_list: bool = None, bid_date_start: str = None,
               bid_date_end: str = None) -> List[Dict]:
        """
        模糊搜索投标项目
        支持按投标单位、招标单位、分项明细、日期范围查询
        """
        cursor = self.conn.cursor()

        conditions = []
        params = []

        if bidder_org:
            conditions.append('bidder_org LIKE ?')
            params.append(f'%{bidder_org}%')

        if tender_org:
            conditions.append('tender_org LIKE ?')
            params.append(f'%{tender_org}%')

        if has_itemized_list is not None:
            conditions.append('has_itemized_list = ?')
            params.append(1 if has_itemized_list else 0)

        if bid_date_start:
            conditions.append('bid_date >= ?')
            params.append(bid_date_start)

        if bid_date_end:
            conditions.append('bid_date <= ?')
            params.append(bid_date_end)

        where_clause = ''
        if conditions:
            where_clause = 'WHERE ' + ' AND '.join(conditions)

        query = f'''
            SELECT * FROM bidding_projects
            {where_clause}
            ORDER BY scan_time DESC
        '''

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_all_records(self) -> List[Dict]:
        """获取所有记录"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM bidding_projects ORDER BY scan_time DESC')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        cursor = self.conn.cursor()

        cursor.execute('SELECT COUNT(*) as total FROM bidding_projects')
        total = cursor.fetchone()['total']

        cursor.execute('''
            SELECT COUNT(DISTINCT bidder_org) as bidders
            FROM bidding_projects
        ''')
        bidders = cursor.fetchone()['bidders']

        cursor.execute('''
            SELECT COUNT(DISTINCT tender_org) as tenders
            FROM bidding_projects
        ''')
        tenders = cursor.fetchone()['tenders']

        return {
            'total_records': total,
            'unique_bidders': bidders,
            'unique_tenders': tenders,
        }
