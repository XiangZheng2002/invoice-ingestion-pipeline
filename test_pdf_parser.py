#!/usr/bin/env python3
"""
PDF/OFD 直接解析测试

自动生成带文字层的测试发票（数电票、旧版电子普票、OFD、内嵌XML、无文字层扫描件），
验证不配置百度OCR也能把发票字段解析出来。

用法：
    python test_pdf_parser.py

以后拿真实发票调整正则时，跑这个脚本做回归。
"""

import os
import shutil
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import pymupdf
except ImportError:
    try:
        import fitz as pymupdf
    except ImportError:
        print('未安装PyMuPDF，请先执行: pip install pymupdf')
        sys.exit(1)

from app.services.pdf_parser import PDFInvoiceParser

FONT = 'china-ss'   # PyMuPDF内置的简体中文字体
failures = []


def check(label, got, want):
    ok = got == want
    print(f"  {'✓' if ok else '✗'} {label}: {got!r}" + ('' if ok else f'   (期望 {want!r})'))
    if not ok:
        failures.append(label)


def make_pdf(path, lines):
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=420)
    for x, y, text, size in lines:
        page.insert_text((x, y), text, fontname=FONT, fontsize=size)
    doc.save(path)
    doc.close()


def test_digital_invoice(workdir, parser):
    """新版数电票：购销方左右并排，靠坐标区分"""
    path = os.path.join(workdir, 'digital.pdf')
    make_pdf(path, [
        (200, 40, '电子发票（普通发票）', 14),
        (360, 70, '发票号码：25312000000123456789', 9),
        (360, 85, '开票日期：2025年01月15日', 9),
        (60, 120, '购买方信息', 9),
        (320, 120, '销售方信息', 9),
        (60, 140, '名称：北京示例科技有限公司', 9),
        (320, 140, '名称：上海测试服务有限公司', 9),
        (60, 155, '统一社会信用代码/纳税人识别号：91110000MA01ABCD2X', 8),
        (320, 155, '统一社会信用代码/纳税人识别号：91310000MA1FL0PQ8G', 8),
        (60, 200, '项目名称   规格型号  单位  数量  单价  金额  税率  税额', 8),
        (60, 220, '*信息技术服务*技术服务费   1   1000.00  1000.00  6%  60.00', 8),
        (60, 250, '合  计        ¥1000.00      ¥60.00', 8),
        (60, 275, '价税合计（大写）壹仟零陆拾圆整 （小写）¥1060.00', 9),
    ])

    print('\n=== 新版数电票 ===')
    result = parser.parse(path)
    check('解析成功', result['success'], True)
    if not result['success']:
        print('   ', result['message'])
        return

    data = result['data']
    check('来源', result['source'], 'pdf')
    check('发票号码', data['invoice_number'], '25312000000123456789')
    check('开票日期', data['invoice_date'], '2025-01-15')
    check('发票类型', data['invoice_type'], '电子发票（普通发票）')
    check('购买方', data['buyer_name'], '北京示例科技有限公司')
    check('销售方', data['seller_name'], '上海测试服务有限公司')
    check('购方税号', data['buyer_tax_num'], '91110000MA01ABCD2X')
    check('销方税号', data['seller_tax_num'], '91310000MA1FL0PQ8G')
    check('金额', data['total_amount'], 1000.0)
    check('税额', data['tax_amount'], 60.0)
    check('价税合计', data['total_with_tax'], 1060.0)


def test_legacy_invoice(workdir, parser):
    """旧版增值税电子普通发票：有发票代码和校验码"""
    path = os.path.join(workdir, 'legacy.pdf')
    make_pdf(path, [
        (200, 40, '增值税电子普通发票', 14),
        (400, 70, '发票代码：011002000611', 9),
        (400, 85, '发票号码：12345678', 9),
        (400, 100, '开票日期：2020年05月20日', 9),
        (330, 115, '校验码：12345 67890 12345 67890', 8),
        (60, 145, '购买方   名称：广州买方贸易有限公司', 9),
        (60, 160, '         纳税人识别号：91440000MA5ABCDE1F', 8),
        (60, 250, '合  计        ¥500.00       ¥30.00', 8),
        (60, 275, '价税合计（大写）伍佰叁拾圆整 （小写）¥530.00', 9),
        (60, 310, '销售方   名称：深圳卖方服务有限公司', 9),
        (60, 325, '         纳税人识别号：91440300MA5FGHIJ2K', 8),
    ])

    print('\n=== 旧版增值税电子普通发票 ===')
    result = parser.parse(path)
    check('解析成功', result['success'], True)
    if not result['success']:
        print('   ', result['message'])
        return

    data = result['data']
    check('发票代码', data['invoice_code'], '011002000611')
    check('发票号码', data['invoice_number'], '12345678')
    check('开票日期', data['invoice_date'], '2020-05-20')
    check('校验码', data['check_code'], '12345678901234567890')
    check('购买方', data['buyer_name'], '广州买方贸易有限公司')
    check('销售方', data['seller_name'], '深圳卖方服务有限公司')
    check('价税合计', data['total_with_tax'], 530.0)


def test_embedded_xml(workdir, parser):
    """PDF内嵌发票XML：最可靠的数据来源"""
    path = os.path.join(workdir, 'embedded.pdf')
    invoice_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<EInvoice><Fphm>25312000000111222333</Fphm><Kprq>20250620</Kprq>'
        '<Gfmc>成都购方科技有限公司</Gfmc><Gfnsrsbh>91510100MA6ABCDE1F</Gfnsrsbh>'
        '<Xfmc>武汉销方服务有限公司</Xfmc><Xfnsrsbh>91420100MA4FGHIJ2K</Xfnsrsbh>'
        '<Hjje>800.00</Hjje><Hjse>48.00</Hjse><Jshj>848.00</Jshj></EInvoice>'
    )
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((60, 80), '发票', fontname=FONT, fontsize=10)
    doc.embfile_add('invoice.xml', invoice_xml.encode('utf-8'))
    doc.save(path)
    doc.close()

    print('\n=== PDF内嵌发票XML ===')
    result = parser.parse(path)
    check('解析成功', result['success'], True)
    if not result['success']:
        print('   ', result['message'])
        return

    data = result['data']
    check('来源', result['source'], 'xml')
    check('发票号码', data['invoice_number'], '25312000000111222333')
    check('开票日期', data['invoice_date'], '2025-06-20')
    check('销售方', data['seller_name'], '武汉销方服务有限公司')
    check('价税合计', data['total_with_tax'], 848.0)
    check('置信度', data['ocr_confidence'], 0.99)


def test_ofd(workdir, parser):
    """OFD格式：zip包，文字在TextCode元素里"""
    path = os.path.join(workdir, 'sample.ofd')
    texts = [
        '电子发票（普通发票）', '发票号码：', '25312000000987654321',
        '开票日期：', '2025年03月10日',
        '名称：', '广州购方有限公司', '名称：', '杭州销方有限公司',
        '合  计', '¥200.00', '¥12.00',
        '价税合计（大写）贰佰壹拾贰圆整', '（小写）', '¥212.00',
    ]
    body = ''.join(f'<ofd:TextObject><ofd:TextCode>{t}</ofd:TextCode></ofd:TextObject>' for t in texts)
    page_xml = (
        '<?xml version="1.0"?>'
        f'<ofd:Page xmlns:ofd="http://www.ofdspec.org/2016"><ofd:Content>{body}</ofd:Content></ofd:Page>'
    )

    with zipfile.ZipFile(path, 'w') as zf:
        zf.writestr('OFD.xml', '<?xml version="1.0"?><ofd:OFD xmlns:ofd="http://www.ofdspec.org/2016"/>')
        zf.writestr('Doc_0/Pages/Page_0/Content.xml', page_xml)

    print('\n=== OFD格式 ===')
    result = parser.parse(path)
    check('解析成功', result['success'], True)
    if not result['success']:
        print('   ', result['message'])
        return

    data = result['data']
    check('来源', result['source'], 'ofd')
    check('发票号码', data['invoice_number'], '25312000000987654321')
    check('开票日期', data['invoice_date'], '2025-03-10')
    check('购买方', data['buyer_name'], '广州购方有限公司')
    check('销售方', data['seller_name'], '杭州销方有限公司')
    check('价税合计', data['total_with_tax'], 212.0)


def test_scanned(workdir, parser):
    """无文字层的扫描件：应该解析失败，交给OCR兜底"""
    path = os.path.join(workdir, 'scanned.pdf')
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=420)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 400, 300))
    pix.clear_with(220)
    page.insert_image(pymupdf.Rect(50, 50, 450, 350), pixmap=pix)
    doc.save(path)
    doc.close()

    print('\n=== 无文字层扫描件 ===')
    result = parser.parse(path)
    check('解析失败（应回退OCR）', result['success'], False)
    check('has_text_layer', parser.has_text_layer(path), False)
    print('    提示:', result['message'])


def main():
    workdir = tempfile.mkdtemp(prefix='invoice_parser_test_')
    parser = PDFInvoiceParser()

    try:
        test_digital_invoice(workdir, parser)
        test_legacy_invoice(workdir, parser)
        test_embedded_xml(workdir, parser)
        test_ofd(workdir, parser)
        test_scanned(workdir, parser)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print()
    if failures:
        print(f'✗ {len(failures)} 项未通过: {failures}')
        return 1

    print('✓ 全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
