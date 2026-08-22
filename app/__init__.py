from flask import Flask
from flask_wtf.csrf import CSRFProtect
import os
from dotenv import load_dotenv

# 路径解析统一放在 app.paths，crypto/日志等底层模块也要用，
# 这里重新导出是为了兼容既有的 import 写法
from app.paths import get_base_dir, get_resource_path, is_frozen

# 加载环境变量
load_dotenv()

csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)

    # Get base directory (project root)
    base_dir = get_base_dir()

    # 配置
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['DATABASE_PATH'] = os.path.join(base_dir, os.getenv('DATABASE_PATH', 'data/invoices.db'))
    app.config['ATTACHMENTS_PATH'] = os.path.join(base_dir, os.getenv('ATTACHMENTS_PATH', 'data/attachments'))
    app.config['EXPORTS_PATH'] = os.path.join(base_dir, os.getenv('EXPORTS_PATH', 'data/exports'))
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

    # 初始化CSRF保护
    csrf.init_app(app)

    # 确保必要的目录存在
    os.makedirs(app.config['ATTACHMENTS_PATH'], exist_ok=True)
    os.makedirs(app.config['EXPORTS_PATH'], exist_ok=True)

    # 初始化日志（打包后没有控制台，诊断信息只能靠日志文件）
    from app.logging_setup import setup_logging
    app.config['LOG_PATH'] = setup_logging()

    # 初始化数据库
    from app import models
    models.init_db(app.config['DATABASE_PATH'])

    # 注册路由
    from app.routes import main, email_routes, invoice, config, upload
    app.register_blueprint(main.bp)
    app.register_blueprint(email_routes.bp)
    app.register_blueprint(invoice.bp)
    app.register_blueprint(config.bp)
    app.register_blueprint(upload.bp)

    return app
