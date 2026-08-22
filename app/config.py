import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """应用配置类"""

    # Flask配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-please-change')

    # 数据库配置
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/invoices.db')

    # 文件存储配置
    ATTACHMENTS_PATH = os.getenv('ATTACHMENTS_PATH', 'data/attachments')
    EXPORTS_PATH = os.getenv('EXPORTS_PATH', 'data/exports')

    # 邮件配置
    # 各服务商的 IMAP 地址见 app/services/mail_providers.py，
    # 这里只保留通用默认端口
    DEFAULT_IMAP_PORT = 993

    # 百度OCR配置
    BAIDU_APP_ID = os.getenv('BAIDU_APP_ID')
    BAIDU_API_KEY = os.getenv('BAIDU_API_KEY')
    BAIDU_SECRET_KEY = os.getenv('BAIDU_SECRET_KEY')

    # 加密密钥
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')

    # 文件上传配置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'pdf', 'ofd', 'png', 'jpg', 'jpeg', 'bmp', 'webp', 'tif', 'tiff'}

    @staticmethod
    def allowed_file(filename):
        """检查文件扩展名是否允许"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS
