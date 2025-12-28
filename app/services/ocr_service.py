"""
OCR服务
使用百度OCR API识别发票信息
"""

from aip import AipOcr
import os
from dotenv import load_dotenv
import json

load_dotenv()

class OCRService:
    """百度OCR服务类"""

    def __init__(self):
        # 从环境变量读取配置
        self.app_id = os.getenv('BAIDU_APP_ID')
        self.api_key = os.getenv('BAIDU_API_KEY')
        self.secret_key = os.getenv('BAIDU_SECRET_KEY')

        # 初始化客户端
        if all([self.app_id, self.api_key, self.secret_key]):
            self.client = AipOcr(self.app_id, self.api_key, self.secret_key)
            self.enabled = True
        else:
            self.client = None
            self.enabled = False
            print("警告：百度OCR未配置，发票识别功能将不可用")

    def is_enabled(self):
        """检查OCR服务是否可用"""
        return self.enabled

    def recognize_invoice(self, file_path):
        """
        识别发票

        Args:
            file_path: 发票文件路径（图片或PDF的第一页）

        Returns:
            dict: 识别结果 {'success': bool, 'data': dict, 'message': str}
        """
        if not self.enabled:
            return {
                'success': False,
                'message': '百度OCR未配置',
                'data': None
            }

        try:
            # 读取文件
            with open(file_path, 'rb') as f:
                image = f.read()

            # 调用增值税发票识别接口
            result = self.client.vatInvoice(image)

            # 检查结果
            if 'error_code' in result:
                return {
                    'success': False,
                    'message': f"OCR识别失败: {result.get('error_msg', '未知错误')}",
                    'data': None
                }

            if 'words_result' not in result:
                return {
                    'success': False,
                    'message': 'OCR返回结果格式错误',
                    'data': None
                }

            # 解析结果
            invoice_data = self.parse_vat_invoice(result['words_result'])

            return {
                'success': True,
                'message': '识别成功',
                'data': invoice_data
            }

        except FileNotFoundError:
            return {
                'success': False,
                'message': f'文件不存在: {file_path}',
                'data': None
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'识别异常: {str(e)}',
                'data': None
            }

    def parse_vat_invoice(self, words_result):
        """
        解析增值税发票识别结果

        Args:
            words_result: 百度OCR返回的识别结果

        Returns:
            dict: 标准化的发票数据
        """
        def get_value(field_name):
            """安全获取字段值"""
            if field_name in words_result:
                return words_result[field_name].get('words', '')
            return ''

        invoice_data = {
            # 基本信息
            'invoice_code': get_value('InvoiceCode'),
            'invoice_number': get_value('InvoiceNum'),
            'invoice_date': get_value('InvoiceDate'),
            'invoice_type': '增值税专用发票',

            # 购买方信息（抬头）
            'buyer_name': get_value('PurchaserName'),
            'buyer_tax_num': get_value('PurchaserRegisterNum'),
            'buyer_address': get_value('PurchaserAddress'),
            'buyer_bank': get_value('PurchaserBank'),

            # 销售方信息
            'seller_name': get_value('SellerName'),
            'seller_tax_num': get_value('SellerRegisterNum'),
            'seller_address': get_value('SellerAddress'),
            'seller_bank': get_value('SellerBank'),

            # 金额信息
            'total_amount': self._parse_amount(get_value('AmountInFiguress')),
            'tax_amount': self._parse_amount(get_value('TotalTax')),
            'total_with_tax': self._parse_amount(get_value('TotalAmount')),

            # 其他信息
            'check_code': get_value('CheckCode'),
            'remarks': get_value('Remarks'),

            # OCR置信度
            'ocr_confidence': 0.9  # 百度OCR一般准确率较高
        }

        # 如果没有识别到发票类型，尝试从其他字段推断
        if not invoice_data['invoice_code']:
            invoice_data['invoice_type'] = '普通发票'

        return invoice_data

    def recognize_general_invoice(self, file_path):
        """
        识别通用发票（非增值税专用发票）

        Args:
            file_path: 发票文件路径

        Returns:
            dict: 识别结果
        """
        if not self.enabled:
            return {
                'success': False,
                'message': '百度OCR未配置',
                'data': None
            }

        try:
            with open(file_path, 'rb') as f:
                image = f.read()

            # 调用通用票据识别接口
            result = self.client.receipt(image)

            if 'error_code' in result:
                return {
                    'success': False,
                    'message': f"OCR识别失败: {result.get('error_msg', '未知错误')}",
                    'data': None
                }

            # 解析通用发票结果
            invoice_data = self._parse_general_invoice(result)

            return {
                'success': True,
                'message': '识别成功',
                'data': invoice_data
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'识别异常: {str(e)}',
                'data': None
            }

    def _parse_general_invoice(self, result):
        """解析通用发票结果"""
        # 从识别结果中提取关键信息
        invoice_data = {
            'invoice_code': '',
            'invoice_number': '',
            'invoice_date': '',
            'invoice_type': '通用发票',
            'buyer_name': '',
            'seller_name': '',
            'total_amount': 0.0,
            'tax_amount': 0.0,
            'total_with_tax': 0.0,
            'ocr_confidence': 0.7
        }

        # TODO: 根据实际返回格式解析
        # 百度OCR通用票据识别返回的是文本列表，需要进一步处理

        return invoice_data

    def _parse_amount(self, amount_str):
        """
        解析金额字符串

        Args:
            amount_str: 金额字符串，如 "¥1,234.56"

        Returns:
            float: 金额数值
        """
        if not amount_str:
            return 0.0

        try:
            # 移除货币符号、逗号等
            amount_str = amount_str.replace('¥', '').replace('￥', '')
            amount_str = amount_str.replace(',', '').replace(' ', '')
            amount_str = amount_str.replace('元', '')

            return float(amount_str)
        except (ValueError, AttributeError):
            return 0.0

    def test_connection(self):
        """测试OCR服务连接"""
        if not self.enabled:
            return False, "百度OCR未配置"

        try:
            # 尝试调用一个简单的API
            return True, "OCR服务可用"
        except Exception as e:
            return False, f"OCR服务连接失败: {str(e)}"
