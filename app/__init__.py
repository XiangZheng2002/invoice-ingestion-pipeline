from flask import Flask
from flask_wtf.csrf import CSRFProtect
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)

    # 配置
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['DATABASE_PATH'] = os.getenv('DATABASE_PATH', 'data/invoices.db')
    app.config['ATTACHMENTS_PATH'] = os.getenv('ATTACHMENTS_PATH', 'data/attachments')
    app.config['EXPORTS_PATH'] = os.getenv('EXPORTS_PATH', 'data/exports')
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

    # 初始化CSRF保护
    csrf.init_app(app)

    # 确保必要的目录存在
    os.makedirs('data/attachments', exist_ok=True)
    os.makedirs('data/exports', exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    # 初始化数据库
    from app import models
    models.init_db(app.config['DATABASE_PATH'])

    # 注册路由
    from app.routes import main, email_routes, invoice
    app.register_blueprint(main.bp)
    app.register_blueprint(email_routes.bp)
    app.register_blueprint(invoice.bp)

    return app
