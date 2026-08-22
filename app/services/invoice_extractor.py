"""
发票信息提取统一入口

对外只暴露一个 extract()，内部按以下顺序尝试：
  1. PDF/OFD 文字层直接解析（离线、免费、准确率高）—— 绝大多数电子发票走这条路
  2. 百度OCR（仅当文件是图片/扫描件，或直接解析失败时）

这样用户在只处理电子发票时完全不需要配置百度OCR。
"""

import os

from app.services.pdf_parser import PDFInvoiceParser
from app.services.file_handler import FileHandler


class InvoiceExtractor:
    """发票识别调度器：直接解析优先，OCR兜底"""

    def __init__(self, db_path=None):
        self.db_path = db_path
        self.pdf_parser = PDFInvoiceParser()
        self.file_handler = FileHandler()
        self._ocr_service = None
        self._ocr_loaded = False

    @property
    def ocr_service(self):
        """延迟加载OCR服务（没装baidu-aip也不影响直接解析）"""
        if not self._ocr_loaded:
            self._ocr_loaded = True
            try:
                from app.services.ocr_service import OCRService
                self._ocr_service = OCRService(self.db_path)
            except Exception as e:
                print(f"OCR服务不可用: {e}")
                self._ocr_service = None
        return self._ocr_service

    def ocr_available(self):
        service = self.ocr_service
        return bool(service and service.is_enabled())

    def extract(self, file_path):
        """
        提取发票信息

        Args:
            file_path: 发票文件路径（PDF / OFD / 图片）

        Returns:
            dict: {
                'success': bool,
                'data': dict|None,      # 发票字段
                'message': str,
                'source': str|None,     # 'xml' / 'pdf' / 'ofd' / 'ocr'
            }
        """
        if not os.path.exists(file_path):
            return {'success': False, 'data': None, 'message': f'文件不存在: {file_path}', 'source': None}

        attempts = []

        # 第一步：PDF/OFD 直接解析
        if PDFInvoiceParser.supports(file_path):
            result = self.pdf_parser.parse(file_path)
            if result['success']:
                return result
            attempts.append(f"直接解析失败({result['message']})")

        # 第二步：OCR兜底
        if not self.ocr_available():
            hint = '；'.join(attempts) if attempts else '该文件是图片，无法直接解析'
            return {
                'success': False,
                'data': None,
                'message': f'{hint}。图片/扫描件需要OCR识别，请到"设置"页填写百度OCR密钥',
                'source': None,
            }

        return self._extract_by_ocr(file_path, attempts)

    def _extract_by_ocr(self, file_path, attempts):
        """把文件转成OCR能处理的图片，再调用百度OCR"""
        success, image_path, error = self.file_handler.process_invoice_file(file_path)
        if not success:
            attempts.append(f'文件预处理失败({error})')
            return {'success': False, 'data': None, 'message': '；'.join(attempts), 'source': None}

        try:
            ocr_result = self.ocr_service.recognize_invoice(image_path)
        finally:
            if image_path != file_path:
                self.file_handler.clean_temp_files([image_path])

        if not ocr_result['success']:
            attempts.append(f"OCR识别失败({ocr_result['message']})")
            return {'success': False, 'data': None, 'message': '；'.join(attempts), 'source': None}

        data = ocr_result['data']
        data['parse_source'] = 'ocr'
        return {'success': True, 'data': data, 'message': 'OCR识别成功', 'source': 'ocr'}

    @staticmethod
    def describe_source(source):
        """把来源翻译成给用户看的说明"""
        return {
            'xml': '发票内嵌数据',
            'pdf': 'PDF文字层',
            'ofd': 'OFD文字内容',
            'ocr': '百度OCR',
        }.get(source, '未知')
