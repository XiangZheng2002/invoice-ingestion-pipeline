"""
本地上传识别

用户直接把发票文件拖进来就能识别，不需要先配置邮箱，
电子发票（PDF/OFD）还不需要配置OCR。
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from app.models import Invoice
from app.services.invoice_extractor import InvoiceExtractor
from app.utils.validators import Validators
from datetime import datetime
import os
import traceback

bp = Blueprint('upload', __name__, url_prefix='/upload')

ALLOWED_EXTENSIONS = {'.pdf', '.ofd', '.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tif', '.tiff'}


def _unique_path(directory, filename):
    """避免同名文件互相覆盖"""
    name, ext = os.path.splitext(Validators.sanitize_filename(filename))
    stamp = datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]
    return os.path.join(directory, f'{name}_{stamp}{ext}')


@bp.route('/')
def upload_page():
    """上传识别页面"""
    extractor = InvoiceExtractor(current_app.config['DATABASE_PATH'])
    return render_template('upload.html', ocr_enabled=extractor.ocr_available())


@bp.route('/api', methods=['POST'])
def api_upload():
    """接收上传的发票文件并识别"""
    db_path = current_app.config['DATABASE_PATH']
    attachments_path = current_app.config['ATTACHMENTS_PATH']

    files = request.files.getlist('files')
    files = [f for f in files if f and f.filename]

    if not files:
        return jsonify({'success': False, 'message': '没有收到文件'})

    extractor = InvoiceExtractor(db_path)
    results = []
    saved_count = 0

    for file_storage in files:
        filename = file_storage.filename
        ext = os.path.splitext(filename)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            results.append({
                'filename': filename,
                'success': False,
                'message': f'不支持的文件类型: {ext or "无扩展名"}',
            })
            continue

        save_path = _unique_path(attachments_path, filename)

        try:
            file_storage.save(save_path)
            result = extractor.extract(save_path)

            if not result['success']:
                results.append({
                    'filename': filename,
                    'success': False,
                    'message': result['message'],
                })
                continue

            data = result['data']
            source = result['source']
            source_label = InvoiceExtractor.describe_source(source)

            # 同一张发票重复上传时不再入库
            existing = Invoice.get_by_number(db_path, data.get('invoice_number'))
            if existing:
                results.append({
                    'filename': filename,
                    'success': True,
                    'duplicate': True,
                    'message': f"发票 {data.get('invoice_number')} 已存在，跳过",
                    'source': source_label,
                    'invoice': _brief(data),
                })
                continue

            data['file_path'] = save_path
            data['notes'] = f'本地上传，识别来源：{source_label}'
            invoice_id = Invoice.create(db_path, data)
            saved_count += 1

            results.append({
                'filename': filename,
                'success': True,
                'duplicate': False,
                'message': f'识别成功（{source_label}）',
                'source': source_label,
                'invoice_id': invoice_id,
                'invoice': _brief(data),
            })

        except Exception as e:
            traceback.print_exc()
            results.append({
                'filename': filename,
                'success': False,
                'message': f'处理失败: {e}',
            })

    failed = sum(1 for r in results if not r['success'])
    duplicates = sum(1 for r in results if r.get('duplicate'))

    message = f'成功识别 {saved_count} 张发票'
    if duplicates:
        message += f'，{duplicates} 张重复跳过'
    if failed:
        message += f'，{failed} 个文件失败'

    return jsonify({
        'success': True,
        'message': message,
        'saved': saved_count,
        'duplicates': duplicates,
        'failed': failed,
        'results': results,
    })


def _brief(data):
    """返回给前端展示的精简字段"""
    return {
        'invoice_number': data.get('invoice_number', ''),
        'invoice_date': data.get('invoice_date', ''),
        'invoice_type': data.get('invoice_type', ''),
        'seller_name': data.get('seller_name', ''),
        'buyer_name': data.get('buyer_name', ''),
        'total_with_tax': data.get('total_with_tax', 0) or 0,
        'tax_amount': data.get('tax_amount', 0) or 0,
        'confidence': data.get('ocr_confidence', 0) or 0,
    }
