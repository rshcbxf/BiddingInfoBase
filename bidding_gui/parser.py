"""
文档解析模块 - 解析 .doc/.docx/.pdf 格式的投标文件
功能：提取项目名称、投标函日期、招标单位、投标单位、分项明细等信息
"""
import re
import os
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class ItemizedDetail:
    """分项明细数据模型"""
    device_name: str = ""  # 设备/项目名称
    brand: str = ""  # 品牌
    model: str = ""  # 型号
    quantity: str = ""  # 数量
    tax_rate: str = ""  # 税率
    unit_price_tax_included: str = ""  # 含税单价
    unit_price_tax_excluded: str = ""  # 不含税单价


@dataclass
class ParsedResult:
    """解析结果数据模型"""
    project_name: str = ""
    bid_date: str = ""  # 投标函日期
    tender_org: str = ""
    bidder_org: str = ""
    has_itemized_list: bool = False  # 是否包含分项/明细章节
    itemized_details: List[ItemizedDetail] = None  # 分项明细列表
    raw_text: str = ""

    def __post_init__(self):
        if self.itemized_details is None:
            self.itemized_details = []


class DocumentParser:
    """文档解析器"""

    # 常见关键词模式
    PATTERNS = {
        'project_name': [
            r'项目名称\s*[：:]\s*([^\n\r]+)',
            r'项\s*目\s*名\s*称\s*[：:]\s*([^\n\r]+)',
            r'招标项目\s*名\s*称\s*[：:]\s*([^\n\r]+)',
            r'工程名称\s*[：:]\s*([^\n\r]+)',
            r'标段名称\s*[：:]\s*([^\n\r]+)',
        ],
        'bid_date': [
            # 投标函落款日期
            r'投\s*标\s*函\s*\n?.{0,50}?\n?\s*([0-9]{4}\s*年\s*[0-9]{1,2}\s*月\s*[0-9]{1,2}\s*日)',
            r'投\s*标\s*人\s*[：:]\s*[^\n]*\n\s*([0-9]{4}\s*年\s*[0-9]{1,2}\s*月\s*[0-9]{1,2}\s*日)',
            r'([0-9]{4}\s*年\s*[0-9]{1,2}\s*月\s*[0-9]{1,2}\s*日)\s*投\s*标',
            r'日\s*期\s*[：:]\s*([0-9]{4}\s*年\s*[0-9]{1,2}\s*月\s*[0-9]{1,2}\s*日)',
            r'签\s*署\s*日\s*期\s*[：:]\s*([0-9]{4}\s*年\s*[0-9]{1,2}\s*月\s*[0-9]{1,2}\s*日)',
            r'([0-9]{4}\s*年\s*[0-9]{1,2}\s*月\s*[0-9]{1,2}\s*日)',
        ],
        'tender_org': [
            r'招\s*标\s*人\s*[：:]\s*([^\n\r]+)',
            r'招\s*标\s*单\s*位\s*[：:]\s*([^\n\r]+)',
            r'建\s*设\s*单\s*位\s*[：:]\s*([^\n\r]+)',
            r'业\s*主\s*单\s*位\s*[：:]\s*([^\n\r]+)',
            r'采\s*购\s*人\s*[：:]\s*([^\n\r]+)',
        ],
        'bidder_org': [
            r'投\s*标\s*人\s*[：:]\s*([^\n\r]+)',
            r'投\s*标\s*单\s*位\s*[：:]\s*([^\n\r]+)',
            r'投\s*标\s*人\s*名\s*称\s*[：:]\s*([^\n\r]+)',
            r'竞\s*标\s*单\s*位\s*[：:]\s*([^\n\r]+)',
            r'供\s*应\s*商\s*[：:]\s*([^\n\r]+)',
            r'中\s*标\s*单\s*位\s*[：:]\s*([^\n\r]+)',
        ],
    }

    # 日期标准化格式
    DATE_PATTERNS = [
        (r'(\d{4}) 年 (\d{1,2}) 月 (\d{1,2}) 日', r'\1-\2-\3'),
        (r'(\d{4})/(\d{1,2})/(\d{1,2})', r'\1-\2-\3'),
        (r'(\d{4})\.(\d{1,2})\.(\d{1,2})', r'\1-\2-\3'),
    ]

    def __init__(self):
        pass

    def parse_file(self, file_path: str) -> ParsedResult:
        """
        解析文件，提取关键信息
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.pdf':
            text = self._parse_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            text = self._parse_doc(file_path)
        else:
            text = ""

        result = ParsedResult(raw_text=text)
        self._extract_info(text, result)

        return result

    def is_bid_document(self, file_path: str, text: str = None) -> bool:
        """
        判断文件是否为投标文件
        判断逻辑：
        1. 先检查是否为应排除的文件类型（封套、封面、备忘、招标等）
        2. 投标文件必须至少包含实质性内容之一：投标函、开标一览表、营业执照
        3. 满足以上条件后，再检查核心关键词或文件名 + 内容组合
        """
        # 检查文件名 - 排除非投标文件类型
        filename = os.path.basename(file_path).lower()
        # 排除规则：
        # 1. 辅助文件：封套、封面、目录、封底、备忘、备注、注意事项
        # 2. 招标文件：招标
        # 3. 格式模板：格式、模板、样表、样张
        # 4. 说明文件：关键点、答疑、澄清
        exclude_keywords = ['封套', '封面', '标书封面', '投标函封面', '目录', '封底', '备忘', '备注', '注意事项', '招标', '格式', '模板', '样表', '样张', '关键点', '答疑', '澄清']
        if any(kw in filename for kw in exclude_keywords):
            return False

        # 检查文件内容
        if text is None or not text.strip():
            return False

        # 实质性内容检查 - 投标文件必须至少包含以下三者之一（带章节编码）
        # 章节编码格式：一、投标函 / （一）投标函 / 1.投标函 / 第一章 投标函
        import re
        substantive_patterns = [
            # 投标函 - 支持多种章节编号格式
            (r'(?:^|\n)\s*(?:第.+?[章编部节]|[（(][^)）]+[)）]|\d+\.|\d+|[一二三四五六七八九十]+[、.])\s*投标函', '投标函'),
            # 开标一览表
            (r'(?:^|\n)\s*(?:第.+?[章编部节]|[（(][^)）]+[)）]|\d+\.|\d+|[一二三四五六七八九十]+[、.])\s*开标一览表', '开标一览表'),
            # 营业执照
            (r'(?:^|\n)\s*(?:第.+?[章编部节]|[（(][^)）]+[)）]|\d+\.|\d+|[一二三四五六七八九十]+[、.])\s*营业执照', '营业执照'),
        ]

        matched_substantive = None
        for pattern, name in substantive_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matched_substantive = name
                break

        # 如果没有实质性内容，直接排除
        if not matched_substantive:
            return False

        # 通过实质性内容检查后，如果匹配的是投标函或开标一览表，需要进一步验证实质性内容
        if matched_substantive in ['投标函', '开标一览表']:
            # 先尝试从内容中提取开标日期，用于后续验证
            bid_date = self._extract_bid_date_for_validation(text)
            return self._validate_bid_letter_or_price_list(text, matched_substantive, bid_date)

        # 如果只匹配到营业执照，需要额外检查是否有其他投标特征
        # 核心关键词（包含任一即可判定为投标文件）
        core_keywords = ['投标函', '投标报价', '开标一览表', '报价一览表']
        for keyword in core_keywords:
            if keyword in text:
                return True

        # 文件名包含"投标"且内容包含"投标人/投标单位/投标书"
        filename_keywords = ['投标', '标书', '响应文件']
        if any(kw in filename for kw in filename_keywords):
            content_keywords = ['投标人', '投标单位', '投标书']
            if any(kw in text for kw in content_keywords):
                return True

        # 内容中包含完整的投标文件特征
        full_content_keywords = [
            '投标函', '投标书', '响应函',
            '投标报价表', '分项报价表',
        ]
        for keyword in full_content_keywords:
            if keyword in text:
                return True

        # 如果只匹配到营业执照，但没有其他投标特征，需要检查是否有图片（营业执照扫描件）
        # 由于文本中无法检测图片，这里放宽条件：有营业执照章节即认为是投标文件
        if matched_substantive == '营业执照':
            return True

        return False

    def _extract_bid_date_for_validation(self, text: str) -> str:
        """
        从文本中提取开标日期（投标函日期），用于验证
        返回格式：YYYY 年 M 月
        """
        import re

        # 尝试从投标函落款提取日期
        patterns = [
            r'([0-9]{4}\s*年\s*[0-9]{1,2}\s*月\s*[0-9]{1,2}\s*日)',
            r'([0-9]{4}\s*年\s*[0-9]{1,2}\s*月)',
            r'日\s*期\s*[：:]\s*([0-9]{4}\s*年\s*[0-9]{1,2}\s*月)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return ""

    def _validate_bid_letter_or_price_list(self, text: str, section_type: str, bid_date: str) -> bool:
        """
        验证投标函或开标一览表章节的实质性内容

        验证条件：
        1. 抬头单位：招标单位或招标代理名称
        2. 投标单位：投标人/投标单位名称
        3. 日期：必须有日期，且年/月与开标日期一致

        注意：对于 PDF 等格式，可能存在多个匹配（如目录和正文），
        本方法会检查所有匹配，只要有一个通过验证即返回 True。

        Returns:
            bool: 验证通过返回 True，否则返回 False
        """
        import re

        # 找到所有投标函/开标一览表章节的位置
        section_pattern = r'(?:^|\n)\s*(?:第.+?[章编部节]|[(][^)）]+[)）]|\d+\.|\d+|[一二三四五六七八九十]+[、.])\s*' + re.escape(section_type)
        matches = list(re.finditer(section_pattern, text, re.IGNORECASE))

        if not matches:
            return False

        # 尝试每个匹配，直到找到一个通过验证的
        for match in matches:
            section_start = match.start()
            section_title_end = match.end()

            # 提取章节内容（到下一章节之前）
            next_section_pattern = r'(?:^|\n)\s*(?:第.+?[章编部节]|[(][^)）]+[)）]|[一二三四五六七八九十]+[、.]\s*[\u4e00-\u9fa5]{2,})'
            next_section_match = re.search(next_section_pattern, text[section_title_end:], re.IGNORECASE)

            if next_section_match:
                section_content = text[section_title_end:section_title_end + next_section_match.start()]
            else:
                section_content = text[section_title_end:]

            # 检查该章节是否通过验证
            if self._check_section_validated(section_content, text, section_start, bid_date):
                return True

        return False

    def _check_section_validated(self, section_content: str, full_text: str, section_start: int, bid_date: str) -> bool:
        """
        检查单个章节是否通过验证

        Returns:
            bool: 验证通过返回 True
        """
        import re

        # 1. 检查抬头单位（招标单位或招标代理）
        tender_org_patterns = [
            r'致\s*[：:]\s*([^\n\r]{4,50})',  # 致：XXX
            r'致函\s*[：:]\s*([^\n\r]{4,50})',  # 致函：XXX
            r'([^\n\r]*(?:招标人 | 招标单位 | 建设单位 | 业主单位 | 采购人)[^\n\r]{0,50})',
        ]

        has_tender_org = False
        for pattern in tender_org_patterns:
            match = re.search(pattern, section_content, re.IGNORECASE)
            if match and len(match.group(1).strip()) >= 4:
                has_tender_org = True
                break

        # 额外检查：抬头单位通常在章节标题后不久出现
        if not has_tender_org:
            # 检查章节标题后 400 字符内是否有单位名称（以冒号结尾，且不是"致："格式）
            header_check = full_text[section_start:section_start + 400]

            # 检查是否有"致："格式
            zhi_match = re.search(r'致\s*[：:]\s*([^\n\r]{4,50})', header_check)
            if zhi_match and len(zhi_match.group(1).strip()) >= 4:
                has_tender_org = True

            # 检查是否有直接单位名称格式（如"四川烟草工业有限责任公司："）
            if not has_tender_org:
                # 匹配以冒号结尾的行，且包含公司/厂/局/中心等字样
                line_pattern = r'\n([^\n]+[：:])'
                for match in re.finditer(line_pattern, header_check):
                    line = match.group(1).rstrip(':：').strip()
                    # 检查是否包含单位字样
                    if any(kw in line for kw in ['公司', '厂', '局', '中心', '单位', '院', '所', '办', '集团', '署']):
                        # 排除非单位名称
                        exclude_words = ['尊敬的', '您好', '此致', '敬礼', '承诺', '注：', '说明', '备注']
                        if not any(ex in line for ex in exclude_words):
                            # 检查长度是否合理（至少 4 个字符）
                            if len(line) >= 4:
                                has_tender_org = True
                                break

        # 2. 检查投标单位
        bidder_org_patterns = [
            r'投\s*标\s*人\s*[：:]?\s*([^\n\r]{4,50})',
            r'投\s*标\s*单\s*位\s*[：:]?\s*([^\n\r]{4,50})',
            r'投\s*标\s*人\s*名\s*称\s*[：:]?\s*([^\n\r]{4,50})',
        ]

        has_bidder_org = False
        for pattern in bidder_org_patterns:
            match = re.search(pattern, section_content, re.IGNORECASE)
            if match:
                org = match.group(1).strip()
                # 排除非具体内容
                if len(org) >= 4 and not re.search(r'（[^)]*）', org):
                    has_bidder_org = True
                    break

        # 3. 检查日期并验证与开标日期的一致性
        date_patterns = [
            r'([0-9]{4}\s*年\s*[0-9]{1,2}\s*月\s*[0-9]{1,2}\s*日)',
            r'([0-9]{4}\s*年\s*[0-9]{1,2}\s*月)',
            r'日\s*期\s*[：:]\s*([0-9]{4}\s*年\s*[0-9]{1,2}\s*月\s*[0-9]{1,2}\s*日)',
        ]

        found_date = None
        for pattern in date_patterns:
            match = re.search(pattern, section_content, re.IGNORECASE)
            if match:
                found_date = match.group(1).strip()
                break

        # 验证日期一致性（年/月部分）
        date_matches = False
        if found_date and bid_date:
            # 提取年月部分进行比较 - 支持多种格式
            # found_date 格式：2024 年 03 月 15 日
            # bid_date 格式：2024 年 03 月 或 2024-03
            found_year = re.search(r'([0-9]{4})\s*年', found_date)
            found_month = re.search(r'年\s*([0-9]{1,2})\s*月', found_date)

            bid_year = re.search(r'([0-9]{4})', bid_date)
            bid_month = None
            month_match = re.search(r'[年\-]([0-9]{1,2})\s*(?:月|\-|$)', bid_date)
            if month_match:
                bid_month = month_match.group(1)

            if found_year and bid_year:
                # 比较年份
                year_same = (found_year.group(1) == bid_year.group(1))
                # 比较月份（如果都能提取到）
                month_same = True
                if found_month and bid_month:
                    month_same = (int(found_month.group(1)) == int(bid_month))

                date_matches = year_same and month_same
            elif found_year:
                # 如果没有开标日期参考，只要有日期即可
                date_matches = True
        elif found_date:
            # 没有开标日期参考，只要有日期即可
            date_matches = True

        # 综合判断
        # 必须同时满足：有抬头单位、有投标单位、有日期
        return has_tender_org and has_bidder_org and date_matches

    def _parse_pdf(self, file_path: str) -> str:
        """解析 PDF 文件"""
        try:
            import pdfplumber
            texts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        texts.append(text)
            return '\n'.join(texts)
        except Exception as e:
            return f"[PDF 解析错误]: {e}"

    def _parse_doc(self, file_path: str) -> str:
        """解析 Word 文档 (.doc 或 .docx)"""
        ext = os.path.splitext(file_path)[1].lower()
        texts = []

        if ext == '.docx':
            try:
                from docx import Document
                doc = Document(file_path)
                for para in doc.paragraphs:
                    if para.text.strip():
                        texts.append(para.text)
                # 提取表格内容 - 使用制表符分隔单元格，便于后续解析
                for table in doc.tables:
                    for row in table.rows:
                        row_text = '\t'.join(cell.text.strip() for cell in row.cells)
                        if row_text.strip():
                            texts.append('[TABLE]' + row_text)
            except Exception as e:
                return f"[DOCX 解析错误]: {e}"

        elif ext == '.doc':
            # 老式 .doc 格式，尝试使用 docx2txt 提取文本，然后用 python-docx 提取表格
            texts = []
            docx2txt_success = False

            try:
                import docx2txt
                texts.append(docx2txt.process(file_path))
                docx2txt_success = True
            except Exception:
                pass

            # 无论 docx2txt 是否成功，都尝试用 python-docx 提取表格
            try:
                from docx import Document
                doc = Document(file_path)
                if not docx2txt_success:
                    # 如果 docx2txt 失败，用 python-docx 提取段落
                    for para in doc.paragraphs:
                        if para.text.strip():
                            texts.append(para.text)
                # 提取表格内容
                for table in doc.tables:
                    for row in table.rows:
                        row_text = '\t'.join(cell.text.strip() for cell in row.cells)
                        if row_text.strip():
                            texts.append('[TABLE]' + row_text)
            except Exception as e:
                if not texts:
                    return f"[DOC 解析错误]: 需要安装额外依赖，{e}"

        return '\n'.join(texts)

    def _extract_info(self, text: str, result: ParsedResult):
        """从文本中提取关键信息"""
        if not text:
            return

        # 提取项目名称
        for pattern in self.PATTERNS['project_name']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result.project_name = match.group(1).strip()
                # 清理常见后缀
                result.project_name = re.sub(
                    r'\s*(标段 | 第.*包).*$', '', result.project_name)
                break

        # 提取投标函日期（落款日期）
        for pattern in self.PATTERNS['bid_date']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                result.bid_date = self._normalize_date(date_str)
                break

        # 提取招标单位
        for pattern in self.PATTERNS['tender_org']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result.tender_org = match.group(1).strip()
                # 清理常见后缀
                result.tender_org = re.sub(
                    r'\s*\(.*?\)\s*$', '', result.tender_org)
                break

        # 如果没有直接匹配到招标单位，尝试从投标函中提取收函单位
        if not result.tender_org:
            tender_from_letter = self._extract_tender_from_bid_letter(text)
            if tender_from_letter:
                result.tender_org = tender_from_letter

        # 提取投标单位
        for pattern in self.PATTERNS['bidder_org']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result.bidder_org = match.group(1).strip()
                # 清理常见后缀
                result.bidder_org = re.sub(r'\s*\(.*?\).*$', '', result.bidder_org)
                result.bidder_org = re.sub(r'\s*[盖含（(].*$', '', result.bidder_org)
                break

        # 检测并提取分项/明细章节
        # 先尝试提取明细数据，只有提取到数据时才标记为有分项/明细
        result.itemized_details = self._extract_itemized_details(text)
        result.has_itemized_list = len(result.itemized_details) > 0

        # 如果没有提取到项目名称，尝试使用文档第一行作为备选
        if not result.project_name and text:
            first_line = text.strip().split('\n')[0].strip()
            if first_line and len(first_line) > 5:
                result.project_name = first_line[:100]  # 限制长度

    def _check_itemized_list(self, text: str) -> bool:
        """
        检测文档是否包含分项/明细章节
        匹配章节名称中包含"分项"或"明细"的内容
        """
        # 章节标题模式（通常以数字开头，后跟标题）
        patterns = [
            r'(?:分项|明细).*(?:表|清单)',  # 分项报价明细表、工程量明细清单等
            r'(?:表|清单).*(?:分项|明细)',  # 报价表分项、设备清单明细等
            r'分项工程',
            r'分项报价',
            r'报价明细',
            r'工程量分项',
            r'设备明细',
            r'货物明细',
            r'清单明细',
            r'投标报价表',
            r'设备清单',
            r'货物清单',
            r'产品清单',
        ]

        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def _extract_itemized_details(self, text: str) -> List[ItemizedDetail]:
        """
        解析分项/明细章节中的表格数据
        提取设备、品牌、型号、数量、税率、含税单价、不含税单价等字段
        """
        details = []

        # 按行分析文本，查找表格数据
        lines = text.split('\n')

        # 列名映射（中文 -> 英文）
        column_mapping = {
            # 设备/产品名称
            '设备名称': 'device_name',
            '设备': 'device_name',
            '产品名称': 'device_name',
            '标的名称': 'device_name',  # 添加标的名称
            '标的': 'device_name',  # 添加标的
            '项目': 'device_name',
            '分项名称': 'device_name',
            '货物名称': 'device_name',
            '需求类型': 'device_name',  # 添加需求类型
            '货物': 'device_name',  # 添加货物
            '品目': 'device_name',  # 添加品目
            '采购品目': 'device_name',  # 添加采购品目
            # 品牌
            '品牌': 'brand',
            '品牌/牌号': 'brand',  # 添加品牌/牌号
            '商标': 'brand',
            '原产地': 'brand',
            # 型号/规格
            '型号': 'model',
            '规格型号': 'model',
            '规格/型号': 'model',  # 添加规格/型号
            '规格': 'model',
            # 数量/单位
            '数量': 'quantity',
            '单位': 'unit',
            # 税率
            '税率': 'tax_rate',
            # 单价
            '单价': 'unit_price',
            '含税单价': 'unit_price_tax_included',
            '单价（元，含税）': 'unit_price_tax_included',  # 添加含税单价格式
            '单价（含税）': 'unit_price_tax_included',
            '不含税单价': 'unit_price_tax_excluded',
            '单价（元，不含税）': 'unit_price_tax_excluded',  # 添加不含税单价格式
            '单价（不含税）': 'unit_price_tax_excluded',
            '投标报价': 'unit_price_tax_included',
            '报价': 'unit_price',
            '合价': 'total_price',
            '总价': 'total_price',
        }

        # 核心列名：只有包含这些列的表格才是设备明细表
        # 必须包含设备名称列 + 数量/单位列
        required_device_columns = {'device_name'}  # 设备名称是必须的
        required_quantity_columns = {'quantity', 'unit'}  # 数量或单位至少有一个

        # 尝试识别表格头部
        in_itemized_table = False
        header_row = None
        header_indices = {}
        consecutive_data_rows = 0  # 连续数据行计数
        table_ended = False  # 表格是否已结束
        has_valid_table = False  # 是否找到有效的设备明细表格
        valid_detail_count = 0  # 有效数据条数计数（用于判断是否可以切换到新表格）

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # 移除表格标记
            if line_stripped.startswith('[TABLE]'):
                line_stripped = line_stripped[7:]

            # 检查是否进入分项/明细章节（标题中包含分项或明细，且有表或清单）
            if re.search(r'(?:分项|明细)', line_stripped) and re.search(r'(?:表|清单)', line_stripped):
                in_itemized_table = True
                continue

            # 如果遇到新的章节标题（不包含分项/明细），结束当前章节
            if re.search(r'^\s*(?:第 [一二三四五六七八九十\d]+[章编部项节]|[\d]+[\.、])', line_stripped):
                if not re.search(r'(?:分项|明细)', line_stripped):
                    in_itemized_table = False


            # 尝试解析表格行
            # 分割方式：制表符、竖线
            if '\t' in line_stripped:
                cells = [c.strip() for c in line_stripped.split('\t') if c.strip()]
            elif '|' in line_stripped:
                cells = [c.strip() for c in line_stripped.split('|') if c.strip()]
            else:
                # 尝试用多个空格分割
                cells = re.split(r'\s{2,}', line_stripped)
                cells = [c.strip() for c in cells if c.strip()]

            # 如果单元格数量太少，跳过
            if len(cells) < 2:
                continue

            # 检查是否是表头
            is_header = False
            matched_columns = set()
            for cell in cells:
                for cn_name, en_name in column_mapping.items():
                    if cn_name in cell:
                        matched_columns.add(cn_name)
                        is_header = True

            # 如果匹配到足够多的分项表关键列，确认是分项表格
            if is_header and len(matched_columns) >= 3:
                # 排除总价表：检查是否包含"总价"、"含税总价"等列名
                # 总价表通常只有 1 行数据，且列名包含"总价"
                has_total_price_col = any('总价' in cell or '含税总价' in cell or '不含税总价' in cell for cell in cells)
                has_unit_col = any('单位' in cell for cell in cells)  # 分项明细表通常有"单位"列

                # 如果是总价表（有总价列但没有单位列），跳过
                if has_total_price_col and not has_unit_col:
                    continue

                header_row = cells
                header_indices = self._match_header_columns(cells, column_mapping)

                # 验证是否包含核心列
                # 1. 必须包含设备名称列
                has_device_name = 'device_name' in header_indices
                # 2. 必须包含数量或单位列
                has_quantity = bool(header_indices.keys() & required_quantity_columns)

                # 只有包含设备名称和数量/单位的表格才是设备明细表
                if has_device_name and has_quantity:
                    # 如果之前已经在处理一个表格但没有提取到有效数据，切换到新表格
                    if in_itemized_table and valid_detail_count == 0:
                        # 放弃之前的表格，使用新表头
                        header_indices = self._match_header_columns(cells, column_mapping)
                        consecutive_data_rows = 0
                    elif not in_itemized_table:
                        in_itemized_table = True
                        has_valid_table = True
                        consecutive_data_rows = 0
                    # 如果已经在处理表格且有有效数据，保持当前表格状态
                else:
                    # 不是设备明细表，继续寻找
                    header_indices = {}
                    continue

                consecutive_data_rows = 0  # 重置计数
                continue

            # 如果遇到合计行，结束当前表格的提取
            if in_itemized_table and re.search(r'(?:合计|总计|小计|汇总|上计)', line_stripped):
                in_itemized_table = False
                header_indices = {}
                table_ended = True  # 标记表格已结束，不再检测新表头
                continue

            # 如果连续处理了很多行但没有提取到有效数据，重置表格状态
            # 这有助于跳过空表格，寻找真正的设备明细表
            # 注意：只有在表头切换后已经处理了至少 10 行的情况下才重置，避免刚切换表头就被重置
            if in_itemized_table and valid_detail_count == 0 and i > 500 and consecutive_data_rows > 10:
                in_itemized_table = False
                header_indices = {}
                table_ended = False

            # 如果连续太多数据行，可能是其他表格，停止提取
            if consecutive_data_rows > 20:
                in_itemized_table = False
                header_indices = {}
                continue

            if not in_itemized_table:
                continue

            # 如果是数据行且有表头
            if header_indices:
                # 获取最大列索引
                max_idx = max(header_indices.values()) if header_indices else 0

                # 放宽条件：只要单元格数量足够提取至少一个字段即可
                if len(cells) > max_idx or (len(cells) >= 2 and header_indices):
                    # 跳过所有单元格内容相同的行（分类标题行）
                    if len(set(cells)) == 1:
                        continue

                    detail = ItemizedDetail()
                    for field, idx in header_indices.items():
                        if idx < len(cells):
                            value = cells[idx].strip()
                            if value:
                                setattr(detail, field, value)

                    # 验证设备名称是否是真正的设备/产品名称
                    # 排除签字、备注、税率、备注等非设备名称
                    invalid_device_keywords = ['签字', '盖章', '备注', '税率', '投标', '招标', '公司', '厂', '署',
                                               '法定代表人', '授权代表', '日期', '注:', '说明', '承诺', '此致',
                                               '序号', '项目名称', '项目编号', '投标总报价', '交货时间', '统一社会',
                                               '签字单位', '单位地址', '联系人', '联系电话', '电话', '传真', '邮箱',
                                               '账户', '账号', '开户行', '经营范围', '注册资本', '企业类型',
                                               '合计', '总计', '小计', '汇总', '元整', '整']
                    is_valid_device = True
                    if detail.device_name:
                        device_stripped = detail.device_name.strip()
                        # 如果设备名称太短（只有 1-2 个字符），可能是无效数据
                        if len(device_stripped) <= 2:
                            is_valid_device = False
                        # 如果设备名称是纯数字，可能是无效数据（如年份、序号等）
                        elif device_stripped.isdigit():
                            is_valid_device = False
                        # 检查是否包含无效关键词
                        for kw in invalid_device_keywords:
                            if kw in detail.device_name:
                                is_valid_device = False
                                break

                    # 只有当至少有一个字段有值且设备名称有效时才添加
                    if is_valid_device and any(getattr(detail, f) for f in ['device_name', 'brand', 'model', 'quantity',
                                                          'tax_rate', 'unit_price_tax_included', 'unit_price_tax_excluded']):
                        details.append(detail)
                        consecutive_data_rows += 1
                        valid_detail_count += 1
                    elif 'device_name' in header_indices:
                        # 如果表头有设备名称列但该行设备名称为空或无效，则跳过该行
                        # 这有助于过滤空表格（如只有序号没有实际设备名称的表格）
                        continue

        # 只有在找到有效表格且提取到至少一条数据时才认为有分项明细
        return details if has_valid_table and len(details) > 0 else []

    def _match_header_columns(self, header_row: List[str], column_mapping: Dict[str, str]) -> Dict[str, int]:
        """
        匹配表头列与字段名
        返回：{字段名：列索引}（每个字段只保留第一个匹配的列索引）
        """
        indices = {}
        used_columns = set()  # 记录已被占用的列，避免重复映射

        # 按列名长度降序排序，优先匹配更长的列名（更精确的匹配）
        sorted_mappings = sorted(column_mapping.items(), key=lambda x: len(x[0]), reverse=True)

        for i, col in enumerate(header_row):
            for cn_name, en_name in sorted_mappings:
                if cn_name in col and i not in used_columns:
                    if en_name not in indices:  # 只保留第一个匹配
                        indices[en_name] = i
                        used_columns.add(i)
                        break  # 找到匹配后跳出，避免同一列被多次匹配
        return indices

    def _normalize_date(self, date_str: str) -> str:
        """标准化日期格式为 YYYY-MM-DD"""
        # 先尝试匹配带"年月日"的格式（在移除之前）
        for pattern, replacement in self.DATE_PATTERNS:
            match = re.search(pattern, date_str)
            if match:
                return re.sub(pattern, replacement, date_str)

        # 移除"日"、"号"等后缀后再尝试匹配
        date_str = re.sub(r'[日号]$', '', date_str)

        for pattern, replacement in self.DATE_PATTERNS:
            match = re.search(pattern, date_str)
            if match:
                return re.sub(pattern, replacement, date_str)

        # 如果无法解析，返回原始字符串
        return date_str

    def _extract_tender_from_bid_letter(self, text: str) -> str:
        """
        从投标函中提取招标单位（收函单位）
        支持多种格式：
        1. 致：[招标单位名称]
        2. 致函：[招标单位名称]
        3. 抬头单位：（投标函标题下方的单位）
        """
        patterns = [
            r'致\s*[：:]\s*([^\n\r]+)',
            r'致\s*函\s*[：:]\s*([^\n\r]+)',
            r'送\s*[：:]\s*([^\n\r]+)',
            r'呈\s*[：:]\s*([^\n\r]+)',
            r'报\s*[：:]\s*([^\n\r]+)',
        ]

        # 先查找投标函相关关键词附近的内容
        keywords = ['投标函', '投标书', '致函', '投标申请']
        search_range = None

        for keyword in keywords:
            idx = text.lower().find(keyword.lower())
            if idx != -1:
                # 取关键词前后 500 字符范围
                start = max(0, idx - 100)
                end = min(len(text), idx + 500)
                search_range = text[start:end]
                break

        # 在限定范围内搜索，如果找不到再用全文
        search_text = search_range if search_range else text

        for pattern in patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                org_name = match.group(1).strip()
                # 过滤掉太短的匹配（可能是"致：此"之类）
                if len(org_name) >= 4:
                    # 清理常见后缀
                    org_name = re.sub(r'\s*\(.*?\)\s*$', '', org_name)
                    org_name = re.sub(r'\s*[，,].*$', '', org_name)
                    return org_name

        # 尝试从抬头提取（投标函标题下方的单位）
        # 格式如：
        #     投标函
        #     某某市人民政府：
        tender_org = self._extract_header_org(text)
        if tender_org:
            return tender_org

        return ""

    def _extract_header_org(self, text: str) -> str:
        """
        从投标函抬头提取单位名称
        匹配格式：
            投标函
            [单位名称]：
            或
            投标函 [单位名称]：
        """
        # 按换行符分割
        lines = text.split('\n')

        # 尝试匹配"投标函\n 单位名称："格式
        bid_letter_pattern = r'投标函\n(.{5,50}[：:])'
        match = re.search(bid_letter_pattern, text)
        if match:
            org_name = match.group(1).rstrip('：:').strip()
            # 清理可能的前置空格
            org_name = org_name.lstrip()
            if len(org_name) >= 4 and ('公司' in org_name or '单位' in org_name or '中心' in org_name or '院' in org_name):
                return org_name

        in_bid_letter = False

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # 检查是否进入投标函部分
            if any(kw in line_stripped for kw in ['投标函', '投标书']):
                in_bid_letter = True
                continue

            if not in_bid_letter:
                continue

            # 在投标函标题后查找抬头单位
            # 匹配以冒号结尾的行，且长度合理（4-50 字符）
            if re.match(r'^[^\s：:]{4,50}[：:]$', line_stripped):
                org_name = line_stripped.rstrip('：:').strip()
                # 排除常见非单位名称
                exclude_patterns = ['尊敬的', '致', '此致', '敬礼', '您好']
                if not any(ep in org_name for ep in exclude_patterns):
                    return org_name

            # 如果已经检查了几行还没找到，停止
            if i > 10:
                break

        return ""

    def extract_with_context(self, text: str, keyword: str,
                             context_lines: int = 2) -> str:
        """
        根据关键词提取上下文信息
        用于手动查找未自动提取到的信息
        """
        lines = text.split('\n')
        results = []

        for i, line in enumerate(lines):
            if keyword.lower() in line.lower():
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                results.extend(lines[start:end])

        return '\n'.join(results)


def test_parser():
    """测试解析器功能"""
    parser = DocumentParser()

    # 测试日期标准化
    test_dates = [
        "2024 年 03 月 15 日",
        "2024/3/5",
        "2024.01.20",
        "2024-06-30",
    ]

    print("日期标准化测试:")
    for date in test_dates:
        print(f"  {date} -> {parser._normalize_date(date)}")

    # 测试信息提取
    sample_text = """
    项目名称：某市智慧平台建设项目
    招标人：某市人民政府办公室
    投标单位：某某科技有限公司
    投标函
    2024 年 06 月 15 日
    分项报价明细表
    """

    result = ParsedResult()
    parser._extract_info(sample_text, result)

    print("\n信息提取测试:")
    print(f"  项目名称：{result.project_name}")
    print(f"  招标单位：{result.tender_org}")
    print(f"  投标单位：{result.bidder_org}")
    print(f"  投标函日期：{result.bid_date}")
    print(f"  分项明细：{result.has_itemized_list}")


if __name__ == '__main__':
    test_parser()
