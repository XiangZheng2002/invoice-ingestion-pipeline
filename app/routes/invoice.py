from flask import Blueprint, render_template, request, jsonify, current_app, send_file
from app.models import Invoice
from app.services.csv_exporter import CSVExporter
import os

bp = Blueprint('invoice', __name__, url_prefix='/invoice')

@bp.route('/list')
def invoice_list():
    """发票列表页面"""
    db_path = current_app.config['DATABASE_PATH']
    invoices = Invoice.get_all(db_path, limit=100)
    return render_template('invoice_list.html', invoices=invoices)

@bp.route('/api/list')
def api_list():
    """获取发票列表API"""
    db_path = current_app.config['DATABASE_PATH']
    invoices = Invoice.get_all(db_path, limit=1000)

    # 转换为字典列表
    invoice_list = []
    for inv in invoices:
        invoice_list.append({
            'id': inv['id'],
            'invoice_code': inv['invoice_code'],
            'invoice_number': inv['invoice_number'],
            'invoice_type': inv['invoice_type'],
            'invoice_date': inv['invoice_date'],
            'buyer_name': inv['buyer_name'],
            'seller_name': inv['seller_name'],
            'total_amount': float(inv['total_amount']) if inv['total_amount'] else 0,
            'tax_amount': float(inv['tax_amount']) if inv['tax_amount'] else 0,
            'total_with_tax': float(inv['total_with_tax']) if inv['total_with_tax'] else 0,
            'created_at': inv['created_at']
        })

    return jsonify({'data': invoice_list})

@bp.route('/export')
def export_csv():
    """导出CSV"""
    try:
        db_path = current_app.config['DATABASE_PATH']
        exports_path = current_app.config['EXPORTS_PATH']

        # 导出CSV
        exporter = CSVExporter(db_path, exports_path)
        csv_file = exporter.export_all_invoices()

        if os.path.exists(csv_file):
            return send_file(
                csv_file,
                as_attachment=True,
                download_name=os.path.basename(csv_file),
                mimetype='text/csv'
            )
        else:
            return jsonify({'success': False, 'message': 'CSV文件生成失败'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'})

@bp.route('/detail/<int:invoice_id>')
def detail(invoice_id):
    """发票详情"""
    db_path = current_app.config['DATABASE_PATH']
    invoice = Invoice.get_by_id(db_path, invoice_id)

    if invoice:
        return jsonify({'success': True, 'data': dict(invoice)})
    else:
        return jsonify({'success': False, 'message': '发票不存在'})
