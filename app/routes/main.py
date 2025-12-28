from flask import Blueprint, render_template, current_app
from app.models import Email, Invoice

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """首页"""
    db_path = current_app.config['DATABASE_PATH']

    # 获取统计数据
    total_emails = Email.count(db_path)
    invoice_emails = Email.count(db_path, is_invoice=True)
    total_invoices = Invoice.count(db_path)
    total_amount = Invoice.get_total_amount(db_path)

    # 获取最近的发票
    recent_invoices = Invoice.get_all(db_path, limit=5)

    return render_template('index.html',
                           total_emails=total_emails,
                           invoice_emails=invoice_emails,
                           total_invoices=total_invoices,
                           total_amount=total_amount,
                           recent_invoices=recent_invoices)

@bp.route('/config')
def config():
    """配置页面"""
    return render_template('config.html')
