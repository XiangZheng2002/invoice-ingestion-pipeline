"""
发票文件直接解析服务

电子发票（数电票、增值税电子普通发票等）的PDF/OFD文件本身带有文字层，
可以直接提取出结构化字段，不需要调用OCR：
  - 准确率高于OCR（是原始数据，不是图像识别）
  - 完全离线、免费，用户无需注册百度云账号
只有扫描件、照片、纯图片发票才需要回退到OCR。

解析优先级：
  1. PDF内嵌的发票XML附件 / OFD包内的发票XML（结构化数据，最可靠）
  2. PDF文字层 / OFD文字内容 + 正则提取
  3. 都失败则返回 success=False，由调用方回退到OCR
"""

import os
import re
import zipfile
import xml.etree.ElementTree as ET

try:
    import pymupdf
except ImportError:  # pragma: no cover - 兼容旧版本PyMuPDF
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None


# ---------- 字段正则 ----------
# 发票中的文字常被拆成单字，字与字之间可能有空格，所以标签都用 \s* 连接

RE_INVOICE_NUMBER = re.compile(r'发\s*票\s*号\s*码\s*[:：]?\s*([0-9]{8,20})')
RE_INVOICE_CODE = re.compile(r'发\s*票\s*代\s*码\s*[:：]?\s*([0-9]{10,12})')
RE_DATE_CN = re.compile(r'开\s*票\s*日\s*期\s*[:：]?\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日')
RE_DATE_ISO = re.compile(r'开\s*票\s*日\s*期\s*[:：]?\s*(\d{4})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{1,2})')
# 价税合计（小写）¥1060.00
RE_TOTAL_WITH_TAX = re.compile(r'[（(]\s*小\s*写\s*[）)]\s*[¥￥]?\s*([\d,]+(?:\.\d{1,2})?)')
# 合计 ¥1000.00 ¥60.00  ->  (不含税金额, 税额)
RE_SUM_LINE = re.compile(r'合\s*计\s*[¥￥]\s*([\d,]+(?:\.\d{1,2})?)\s*[¥￥]\s*([\d,]+(?:\.\d{1,2})?)')
RE_CHECK_CODE = re.compile(r'校\s*验\s*码\s*[:：]?\s*((?:\d\s*){20})')
RE_TAX_ID = re.compile(
    r'(?:统一社会信用代码\s*/\s*纳税人识别号|纳税人识别号|统一社会信用代码)\s*[:：]?\s*([0-9A-Z]{15,20})'
)

# 名称字段后面一旦出现这些标签就该截断
# （购销方并排的版式里，一行内可能同时有两个"名称："）
NAME_STOP_PATTERN = (
    r'名\s*称\s*[:：]|统一社会信用代码|纳税人识别号|项\s*目|规\s*格|'
    r'销\s*售\s*方|购\s*买\s*方|地\s*址|电\s*话|开\s*户\s*行|账\s*号|'
    r'合\s*计|价\s*税|备\s*注|金\s*额|税\s*额'
)
NAME_STOP_RE = re.compile(NAME_STOP_PATTERN)
# 取整行剩余内容（配合坐标定位时使用，由 clean_name 负责截断）
RE_NAME_VALUE = re.compile(r'名\s*称\s*[:：]\s*(.+)')
# 按文本顺序逐个提取名称，非贪婪 + 前瞻，保证一行内多个"名称："都能取到
RE_NAME_SEQ = re.compile(
    r'名\s*称\s*[:：]\s*(.+?)(?=\s*(?:' + NAME_STOP_PATTERN + r')|$)',
    re.M
)

# 发票类型识别，越具体的越靠前
INVOICE_TYPE_PATTERNS = [
    (r'电\s*子\s*发\s*票\s*[（(]\s*增值税专用发票\s*[）)]', '电子发票（增值税专用发票）'),
    (r'电\s*子\s*发\s*票\s*[（(]\s*普通发票\s*[）)]', '电子发票（普通发票）'),
    (r'电\s*子\s*发\s*票\s*[（(]\s*铁路电子客票\s*[）)]', '电子发票（铁路电子客票）'),
    (r'电\s*子\s*发\s*票\s*[（(]\s*航空运输电子客票行程单\s*[）)]', '电子发票（航空运输电子客票行程单）'),
    (r'增\s*值\s*税\s*电\s*子\s*专\s*用\s*发\s*票', '增值税电子专用发票'),
    (r'增\s*值\s*税\s*电\s*子\s*普\s*通\s*发\s*票', '增值税电子普通发票'),
    (r'增\s*值\s*税\s*专\s*用\s*发\s*票', '增值税专用发票'),
    (r'增\s*值\s*税\s*普\s*通\s*发\s*票', '增值税普通发票'),
    (r'航空运输电子客票行程单', '航空运输电子客票行程单'),
    (r'铁路电子客票|火\s*车\s*票', '铁路电子客票'),
]

# 发票XML中的标签名 -> 标准字段名（税总数电票XML及常见变体，大小写不敏感）
XML_TAG_MAP = {
    'fphm': 'invoice_number', '发票号码': 'invoice_number',
    'fpdm': 'invoice_code', '发票代码': 'invoice_code',
    'kprq': 'invoice_date', '开票日期': 'invoice_date',
    'gfmc': 'buyer_name', '购买方名称': 'buyer_name', 'gmfmc': 'buyer_name',
    'gfnsrsbh': 'buyer_tax_num', '购买方纳税人识别号': 'buyer_tax_num', 'gmfnsrsbh': 'buyer_tax_num',
    'xfmc': 'seller_name', '销售方名称': 'seller_name', 'xsfmc': 'seller_name',
    'xfnsrsbh': 'seller_tax_num', '销售方纳税人识别号': 'seller_tax_num', 'xsfnsrsbh': 'seller_tax_num',
    'hjje': 'total_amount', '合计金额': 'total_amount',
    'hjse': 'tax_amount', '合计税额': 'tax_amount',
    'jshj': 'total_with_tax', '价税合计': 'total_with_tax',
    'bz': 'remarks', '备注': 'remarks',
}


def parse_amount(value):
    """把 '¥1,234.56' / '1234.56元' 之类解析成 float"""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value)
    for ch in ['¥', '￥', ',', ' ', '元', ' ']:
        text = text.replace(ch, '')
    try:
        return float(text)
    except ValueError:
        return 0.0


def normalize_date(year, month, day):
    """统一成 YYYY-MM-DD"""
    try:
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except (TypeError, ValueError):
        return ''


def clean_name(raw):
    """清理名称字段：截断到下一个标签，去掉首尾杂字符"""
    if not raw:
        return ''

    name = raw.strip()
    # 名称后面可能紧跟其他标签（尤其是购销方并排的版式），截断掉
    match = NAME_STOP_RE.search(name)
    if match and match.start() > 0:
        name = name[:match.start()]
    # 两个及以上连续空格通常是列间距
    name = re.split(r'\s{2,}', name)[0]
    name = name.strip(' :：\t\r\n')
    return name[:100]


class PDFInvoiceParser:
    """从PDF/OFD文字层直接提取发票信息（无需OCR）"""

    SUPPORTED_EXTENSIONS = {'.pdf', '.ofd'}

    @staticmethod
    def is_available():
        """PyMuPDF是否可用（OFD解析只依赖标准库，PDF解析需要PyMuPDF）"""
        return pymupdf is not None

    @classmethod
    def supports(cls, file_path):
        return os.path.splitext(file_path)[1].lower() in cls.SUPPORTED_EXTENSIONS

    def parse(self, file_path):
        """
        解析发票文件

        Args:
            file_path: PDF或OFD文件路径

        Returns:
            dict: {'success': bool, 'data': dict|None, 'message': str, 'source': str}
                  source 取值：'xml'（内嵌结构化数据）/ 'pdf' / 'ofd'
        """
        if not os.path.exists(file_path):
            return self._fail(f'文件不存在: {file_path}')

        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == '.pdf':
                return self._parse_pdf(file_path)
            elif ext == '.ofd':
                return self._parse_ofd(file_path)
            else:
                return self._fail(f'直接解析不支持的文件类型: {ext}')
        except Exception as e:
            return self._fail(f'文件解析异常: {e}')

    # ---------- PDF ----------

    def _parse_pdf(self, file_path):
        if pymupdf is None:
            return self._fail('PyMuPDF未安装，无法直接解析PDF')

        doc = pymupdf.open(file_path)
        try:
            # 1. 优先读PDF内嵌的发票XML附件（数电票常见）
            xml_data = self._parse_embedded_xml(doc)
            if xml_data:
                return self._build_result(xml_data, source='xml', base_confidence=0.99)

            # 2. 退而使用文字层
            text = '\n'.join(page.get_text() for page in doc)
            if len(text.strip()) < 20:
                return self._fail('PDF没有文字层（可能是扫描件），需要OCR识别')

            data = self.parse_text(text)

            # 用坐标区分并排的购买方/销售方，比纯文本顺序可靠，覆盖上面的结果
            data.update(self._fields_by_column(doc[0]))

            return self._build_result(data, source='pdf', base_confidence=0.95)
        finally:
            doc.close()

    def _parse_embedded_xml(self, doc):
        """读取PDF内嵌的发票XML附件"""
        try:
            count = doc.embfile_count()
        except Exception:
            return None

        for i in range(count):
            try:
                info = doc.embfile_info(i)
                name = (info.get('filename') or info.get('name') or '').lower()
                content = doc.embfile_get(i)
            except Exception:
                continue

            if not content:
                continue
            if not (name.endswith('.xml') or content.lstrip()[:5].lower() == b'<?xml'):
                continue

            data = self._parse_invoice_xml(content)
            if data:
                return data
        return None

    def _fields_by_column(self, page):
        """
        用文字坐标区分购买方（左列）和销售方（右列）

        数电票的购销方信息是左右并排的，纯按文本顺序取"名称："容易错位，
        这里按x坐标分列：最左边的是购买方，最右边的是销售方。
        """
        result = {}
        try:
            words = page.get_text('words')
        except Exception:
            return result

        if not words:
            return result

        def collect(label_keyword, regex):
            """找出所有含关键字的行，返回 [(x0, 匹配值), ...]"""
            hits = []
            for x0, y0, x1, y1, word, *_ in words:
                if label_keyword not in word:
                    continue
                # 拼接同一行、从该词开始往右的所有文字
                line = ''.join(
                    w for wx0, wy0, wx1, wy1, w, *_ in words
                    if abs(wy0 - y0) < 3 and wx0 >= x0 - 0.5
                )
                match = regex.search(line)
                if match:
                    hits.append((x0, match.group(1)))
            hits.sort(key=lambda item: item[0])
            return hits

        names = collect('名称', RE_NAME_VALUE)
        if len(names) >= 2:
            result['buyer_name'] = clean_name(names[0][1])
            result['seller_name'] = clean_name(names[-1][1])
        elif len(names) == 1:
            result['buyer_name'] = clean_name(names[0][1])

        tax_ids = collect('识别号', RE_TAX_ID) or collect('信用代码', RE_TAX_ID)
        if len(tax_ids) >= 2:
            result['buyer_tax_num'] = tax_ids[0][1]
            result['seller_tax_num'] = tax_ids[-1][1]
        elif len(tax_ids) == 1:
            result['buyer_tax_num'] = tax_ids[0][1]

        return {k: v for k, v in result.items() if v}

    # ---------- OFD ----------

    def _parse_ofd(self, file_path):
        """
        OFD是国内电子发票的另一种常见格式，本质是一个zip包，
        页面内容以XML描述，文字在 <TextCode> 元素里。
        """
        if not zipfile.is_zipfile(file_path):
            return self._fail('OFD文件格式无效（不是有效的zip包）')

        with zipfile.ZipFile(file_path) as zf:
            names = zf.namelist()

            # 1. 包内如果直接带发票XML，优先用它
            for name in names:
                if not name.lower().endswith('.xml'):
                    continue
                if 'page' in name.lower() or 'document' in name.lower():
                    continue
                data = self._parse_invoice_xml(zf.read(name))
                if data:
                    return self._build_result(data, source='xml', base_confidence=0.99)

            # 2. 提取页面上的文字
            page_files = sorted(n for n in names if n.lower().endswith('.xml') and 'pages/' in n.lower())
            if not page_files:
                page_files = sorted(n for n in names if n.lower().endswith('.xml'))

            chunks = []
            for name in page_files:
                try:
                    root = ET.fromstring(zf.read(name))
                except ET.ParseError:
                    continue
                for el in root.iter():
                    if el.tag.split('}')[-1] == 'TextCode' and el.text:
                        chunks.append(el.text)

        text = ' '.join(chunks)
        if len(text.strip()) < 20:
            return self._fail('OFD文件中未提取到文字内容')

        data = self.parse_text(text)
        return self._build_result(data, source='ofd', base_confidence=0.9)

    # ---------- 通用解析 ----------

    def _parse_invoice_xml(self, content):
        """按标签名提取发票XML中的字段（不依赖元素顺序和命名空间）"""
        try:
            root = ET.fromstring(content)
        except (ET.ParseError, ValueError):
            return None

        data = {}
        for el in root.iter():
            tag = el.tag.split('}')[-1].lower()
            field = XML_TAG_MAP.get(tag)
            if field and el.text and el.text.strip() and not data.get(field):
                data[field] = el.text.strip()

        if not data.get('invoice_number'):
            return None

        # 金额字段转成数值
        for field in ['total_amount', 'tax_amount', 'total_with_tax']:
            data[field] = parse_amount(data.get(field))

        # 日期可能是 20250115 或 2025-01-15 或 2025年01月15日
        raw_date = data.get('invoice_date', '')
        digits = re.sub(r'\D', '', raw_date)
        if len(digits) == 8:
            data['invoice_date'] = normalize_date(digits[:4], digits[4:6], digits[6:8])

        return data

    def parse_text(self, text):
        """从发票文字中提取各字段"""
        data = {
            'invoice_code': '',
            'invoice_number': '',
            'invoice_date': '',
            'invoice_type': '',
            'buyer_name': '',
            'buyer_tax_num': '',
            'seller_name': '',
            'seller_tax_num': '',
            'total_amount': 0.0,
            'tax_amount': 0.0,
            'total_with_tax': 0.0,
            'check_code': '',
            'remarks': '',
        }

        match = RE_INVOICE_NUMBER.search(text)
        if match:
            data['invoice_number'] = match.group(1)

        match = RE_INVOICE_CODE.search(text)
        if match:
            data['invoice_code'] = match.group(1)

        match = RE_DATE_CN.search(text) or RE_DATE_ISO.search(text)
        if match:
            data['invoice_date'] = normalize_date(*match.groups())

        match = RE_CHECK_CODE.search(text)
        if match:
            data['check_code'] = re.sub(r'\s', '', match.group(1))

        # 发票类型
        for pattern, type_name in INVOICE_TYPE_PATTERNS:
            if re.search(pattern, text):
                data['invoice_type'] = type_name
                break
        if not data['invoice_type']:
            data['invoice_type'] = '电子发票'

        # 金额：价税合计（小写）最可靠
        match = RE_TOTAL_WITH_TAX.search(text)
        if match:
            data['total_with_tax'] = parse_amount(match.group(1))

        match = RE_SUM_LINE.search(text)
        if match:
            data['total_amount'] = parse_amount(match.group(1))
            data['tax_amount'] = parse_amount(match.group(2))

        # 互相推算缺失的金额
        if data['total_with_tax'] and data['total_amount'] and not data['tax_amount']:
            data['tax_amount'] = round(data['total_with_tax'] - data['total_amount'], 2)
        if data['total_with_tax'] and data['tax_amount'] and not data['total_amount']:
            data['total_amount'] = round(data['total_with_tax'] - data['tax_amount'], 2)
        if data['total_amount'] and data['tax_amount'] and not data['total_with_tax']:
            data['total_with_tax'] = round(data['total_amount'] + data['tax_amount'], 2)

        # 购销方（按文本顺序，坐标解析会在后面覆盖更准的结果）
        names = [clean_name(m.group(1)) for m in RE_NAME_SEQ.finditer(text)]
        names = [n for n in names if n]
        if len(names) >= 2:
            data['buyer_name'] = names[0]
            data['seller_name'] = names[1]
        elif len(names) == 1:
            data['buyer_name'] = names[0]

        tax_ids = [m.group(1) for m in RE_TAX_ID.finditer(text)]
        if len(tax_ids) >= 2:
            data['buyer_tax_num'] = tax_ids[0]
            data['seller_tax_num'] = tax_ids[1]
        elif len(tax_ids) == 1:
            data['buyer_tax_num'] = tax_ids[0]

        return data

    # ---------- 结果封装 ----------

    def _build_result(self, data, source, base_confidence):
        """补全字段、计算置信度，并判断是否算解析成功"""
        full = {
            'invoice_code': '',
            'invoice_number': '',
            'invoice_date': '',
            'invoice_type': '电子发票',
            'buyer_name': '',
            'buyer_tax_num': '',
            'seller_name': '',
            'seller_tax_num': '',
            'total_amount': 0.0,
            'tax_amount': 0.0,
            'total_with_tax': 0.0,
            'check_code': '',
            'remarks': '',
        }
        full.update({k: v for k, v in data.items() if v not in (None, '')})

        # 关键字段齐不齐决定置信度
        key_fields = ['invoice_number', 'invoice_date', 'total_with_tax', 'seller_name']
        found = sum(1 for f in key_fields if full.get(f))
        full['ocr_confidence'] = round(base_confidence * found / len(key_fields), 2)
        full['parse_source'] = source

        # 号码和金额都拿不到，说明没解析出有效发票，交给OCR兜底
        has_number = bool(full['invoice_number'] or full['invoice_code'])
        if not (has_number and full['total_with_tax'] > 0):
            return self._fail('文字层中未提取到有效的发票号码或金额，建议使用OCR识别')

        return {
            'success': True,
            'message': f'直接解析成功（来源：{source}）',
            'data': full,
            'source': source,
        }

    def _fail(self, message):
        return {'success': False, 'message': message, 'data': None, 'source': None}

    def has_text_layer(self, file_path):
        """判断PDF是否含文字层（用于决定要不要走OCR）"""
        if pymupdf is None or not file_path.lower().endswith('.pdf'):
            return False
        try:
            with pymupdf.open(file_path) as doc:
                return any(len(page.get_text().strip()) > 20 for page in doc)
        except Exception:
            return False
