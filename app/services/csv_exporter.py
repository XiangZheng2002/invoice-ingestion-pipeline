import csv
import os
from datetime import datetime
from app.models import Invoice as InvoiceModel

class CSVExporter:
    """CSV导出服务类"""

    def __init__(self, db_path, exports_path):
        self.db_path = db_path
        self.exports_path = exports_path

        # 确保导出目录存在
        os.makedirs(exports_path, exist_ok=True)

    def export_all_invoices(self):
        """导出所有发票到CSV"""
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'invoices_{timestamp}.csv'
        filepath = os.path.join(self.exports_path, filename)

        # 获取所有发票
        invoices = InvoiceModel.get_all(self.db_path, limit=10000)

        # CSV字段
        fieldnames = [
            '发票号码',
            '发票代码',
            '发票类型',
            '开票日期',
            '购买方名称',
            '销售方名称',
            '金额合计',
            '税额',
            '价税合计',
            '备注',
            '录入时间'
        ]

        # 写入CSV
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # 写入表头
            writer.writeheader()

            # 写入数据
            for invoice in invoices:
                writer.writerow({
                    '发票号码': invoice['invoice_number'] or '',
                    '发票代码': invoice['invoice_code'] or '',
                    '发票类型': invoice['invoice_type'] or '',
                    '开票日期': invoice['invoice_date'] or '',
                    '购买方名称': invoice['buyer_name'] or '',
                    '销售方名称': invoice['seller_name'] or '',
                    '金额合计': f"{float(invoice['total_amount']):.2f}" if invoice['total_amount'] else '0.00',
                    '税额': f"{float(invoice['tax_amount']):.2f}" if invoice['tax_amount'] else '0.00',
                    '价税合计': f"{float(invoice['total_with_tax']):.2f}" if invoice['total_with_tax'] else '0.00',
                    '备注': invoice['notes'] or '',
                    '录入时间': invoice['created_at'] or ''
                })

        return filepath

    def export_filtered_invoices(self, start_date=None, end_date=None, buyer_name=None):
        """导出筛选后的发票"""
        # TODO: 实现筛选逻辑
        pass

    def append_invoice(self, invoice_data, csv_path):
        """追加单条发票到CSV"""
        fieldnames = [
            '发票号码', '发票代码', '发票类型', '开票日期',
            '购买方名称', '销售方名称', '金额合计', '税额', '价税合计'
        ]

        # 如果文件不存在，创建并写入表头
        file_exists = os.path.exists(csv_path)

        with open(csv_path, 'a', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            writer.writerow({
                '发票号码': invoice_data.get('invoice_number', ''),
                '发票代码': invoice_data.get('invoice_code', ''),
                '发票类型': invoice_data.get('invoice_type', ''),
                '开票日期': invoice_data.get('invoice_date', ''),
                '购买方名称': invoice_data.get('buyer_name', ''),
                '销售方名称': invoice_data.get('seller_name', ''),
                '金额合计': f"{float(invoice_data.get('total_amount', 0)):.2f}",
                '税额': f"{float(invoice_data.get('tax_amount', 0)):.2f}",
                '价税合计': f"{float(invoice_data.get('total_with_tax', 0)):.2f}"
            })
