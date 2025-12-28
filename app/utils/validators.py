import re
from datetime import datetime

class Validators:
    """数据验证工具类"""

    @staticmethod
    def is_valid_email(email):
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    @staticmethod
    def is_valid_date(date_string, date_format='%Y-%m-%d'):
        """验证日期格式"""
        try:
            datetime.strptime(date_string, date_format)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_qq_email(email):
        """检查是否为QQ邮箱"""
        return email.lower().endswith('@qq.com')

    @staticmethod
    def sanitize_filename(filename):
        """清理文件名，移除不安全字符"""
        # 移除路径分隔符和其他危险字符
        dangerous_chars = ['/', '\\', '..', ':', '*', '?', '"', '<', '>', '|']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        return filename

    @staticmethod
    def is_valid_invoice_amount(amount):
        """验证发票金额"""
        try:
            amount_float = float(amount)
            return amount_float >= 0
        except (ValueError, TypeError):
            return False
