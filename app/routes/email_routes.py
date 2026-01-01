from flask import Blueprint, render_template, request, jsonify, current_app
from app.models import Email, Invoice, Config as ConfigModel, get_db_connection
from app.services.email_service import EmailService
from app.services.invoice_detector import InvoiceDetector
from app.services.ocr_service import OCRService
from app.services.file_handler import FileHandler
from app.utils.crypto import CryptoUtil
import traceback
import os

bp = Blueprint('email', __name__, url_prefix='/email')

@bp.route('/list')
def email_list():
    """邮件列表页面"""
    db_path = current_app.config['DATABASE_PATH']
    emails = Email.get_all(db_path, limit=100)

    # 获取配置的日期范围
    since_date = ConfigModel.get(db_path, 'since_date')
    before_date = ConfigModel.get(db_path, 'before_date')

    return render_template('email_list.html', emails=emails, since_date=since_date, before_date=before_date)

@bp.route('/get_config', methods=['GET'])
def get_config():
    """获取邮箱配置"""
    try:
        db_path = current_app.config['DATABASE_PATH']
        email_address = ConfigModel.get(db_path, 'email_address')
        password = ConfigModel.get(db_path, 'email_password')
        since_date = ConfigModel.get(db_path, 'since_date')
        before_date = ConfigModel.get(db_path, 'before_date')

        return jsonify({
            'success': True,
            'data': {
                'email': email_address or '',
                'password': password or '',
                'since_date': since_date or '',
                'before_date': before_date or ''
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'获取配置失败: {str(e)}'})

@bp.route('/save_config', methods=['POST'])
def save_config():
    """保存邮箱配置"""
    try:
        data = request.get_json()
        email_address = data.get('email')
        password = data.get('password')
        since_date = data.get('since_date')
        before_date = data.get('before_date')

        if not all([email_address, password]):
            return jsonify({'success': False, 'message': '邮箱地址和密码不能为空'})

        # 保存配置到数据库（密码加密）
        db_path = current_app.config['DATABASE_PATH']
        ConfigModel.set(db_path, 'email_address', email_address, encrypted=False)
        ConfigModel.set(db_path, 'email_password', password, encrypted=True)
        if since_date:
            ConfigModel.set(db_path, 'since_date', since_date, encrypted=False)
        if before_date:
            ConfigModel.set(db_path, 'before_date', before_date, encrypted=False)
        else:
            # 如果没有终止日期，删除配置
            ConfigModel.set(db_path, 'before_date', '', encrypted=False)

        return jsonify({'success': True, 'message': '配置保存成功'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'保存失败: {str(e)}'})

@bp.route('/test_connection', methods=['POST'])
def test_connection():
    """测试邮箱连接"""
    try:
        data = request.get_json()
        email_address = data.get('email')
        password = data.get('password')

        if not all([email_address, password]):
            return jsonify({'success': False, 'message': '邮箱地址和密码不能为空'})

        # 测试连接
        email_service = EmailService()
        success, message = email_service.connect(email_address, password)

        if success:
            email_service.disconnect()
            return jsonify({'success': True, 'message': '连接成功！'})
        else:
            return jsonify({'success': False, 'message': message})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'连接失败: {str(e)}'})

@bp.route('/fetch_emails', methods=['POST'])
def fetch_emails():
    """获取邮件列表"""
    try:
        data = request.get_json()
        since_date_str = data.get('since_date')
        before_date_str = data.get('before_date')

        # 从数据库读取配置
        db_path = current_app.config['DATABASE_PATH']
        email_address = ConfigModel.get(db_path, 'email_address')
        password = ConfigModel.get(db_path, 'email_password')

        # 如果没有传递日期，从配置中读取
        if not since_date_str:
            since_date_str = ConfigModel.get(db_path, 'since_date')
        if not before_date_str:
            before_date_str = ConfigModel.get(db_path, 'before_date')

        if not all([email_address, password]):
            return jsonify({'success': False, 'message': '请先配置邮箱信息'})

        # 连接邮箱
        email_service = EmailService()
        success, message = email_service.connect(email_address, password)

        if not success:
            return jsonify({'success': False, 'message': message})

        # 获取邮件
        from datetime import datetime, timedelta

        # 解析起始日期
        if since_date_str:
            try:
                since_date = datetime.strptime(since_date_str, '%Y-%m-%d')
            except:
                since_date = datetime.now() - timedelta(days=30)
        else:
            # 默认获取最近30天
            since_date = datetime.now() - timedelta(days=30)

        # 解析终止日期
        before_date = None
        if before_date_str:
            try:
                before_date = datetime.strptime(before_date_str, '%Y-%m-%d')
            except:
                before_date = None

        print(f"获取邮件范围: {since_date.date()} 到 {before_date.date() if before_date else '最新'}")

        email_ids = email_service.fetch_emails(since_date, before_date)

        total_emails = len(email_ids)
        print(f"找到 {total_emails} 封邮件，准备全部处理")

        # 保存到数据库 - 处理所有邮件，不限制数量
        count = 0
        failed = 0
        for email_id in email_ids:  # 处理所有邮件
            try:
                email_data = email_service.parse_email(email_id)
                Email.create(db_path, email_data)
                count += 1

                # 每处理10封打印一次进度
                if count % 10 == 0:
                    print(f"已处理 {count}/{total_emails} 封邮件...")
            except Exception as e:
                print(f"解析邮件失败 {email_id}: {e}")
                failed += 1
                continue

        email_service.disconnect()

        message = f'成功获取 {count} 封邮件'
        if failed > 0:
            message += f'，{failed} 封失败'

        return jsonify({
            'success': True,
            'message': message,
            'count': count,
            'total': total_emails,
            'failed': failed
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'获取邮件失败: {str(e)}'})

@bp.route('/process_invoices', methods=['POST'])
def process_invoices():
    """处理发票识别"""
    try:
        db_path = current_app.config['DATABASE_PATH']
        attachments_path = current_app.config['ATTACHMENTS_PATH']

        # 初始化服务
        detector = InvoiceDetector()
        ocr_service = OCRService()
        file_handler = FileHandler()
        email_service = EmailService()

        # 检查OCR服务是否可用
        if not ocr_service.is_enabled():
            return jsonify({
                'success': False,
                'message': '百度OCR未配置，请在.env文件中配置BAIDU_APP_ID、BAIDU_API_KEY、BAIDU_SECRET_KEY'
            })

        # 获取配置
        email_address = ConfigModel.get(db_path, 'email_address')
        password = ConfigModel.get(db_path, 'email_password')

        if not all([email_address, password]):
            return jsonify({'success': False, 'message': '请先配置邮箱信息'})

        # 连接邮箱
        success, message = email_service.connect(email_address, password)
        if not success:
            return jsonify({'success': False, 'message': f'邮箱连接失败: {message}'})

        # 获取未处理的邮件
        emails = Email.get_all(db_path, limit=100)
        processed_count = 0
        invoice_count = 0

        for email_row in emails:
            if email_row['processed']:
                continue

            try:
                # 重新获取邮件完整数据
                email_data = email_service.parse_email(email_row['email_id'].encode())

                # 检测是否为发票邮件
                is_invoice = detector.is_invoice_email(email_data)

                if is_invoice:
                    # 提取发票附件
                    invoice_files = detector.extract_invoice_files(email_data)

                    for att in invoice_files:
                        # 保存附件
                        att_path = email_service.download_attachment(att, attachments_path)

                        if att_path:
                            # 处理文件
                            success, image_path, error = file_handler.process_invoice_file(att_path)

                            if success:
                                # OCR识别
                                ocr_result = ocr_service.recognize_invoice(image_path)

                                if ocr_result['success']:
                                    # 保存发票数据
                                    invoice_data = ocr_result['data']
                                    invoice_data['email_id'] = email_row['email_id']
                                    invoice_data['file_path'] = att_path

                                    Invoice.create(db_path, invoice_data)
                                    invoice_count += 1

                                # 清理临时文件
                                if image_path != att_path:
                                    file_handler.clean_temp_files([image_path])

                # 标记邮件为已处理
                processed_count += 1

            except Exception as e:
                print(f"处理邮件失败 {email_row['id']}: {e}")
                continue

        email_service.disconnect()

        return jsonify({
            'success': True,
            'message': f'处理完成！识别到 {invoice_count} 张发票',
            'processed': processed_count,
            'invoices': invoice_count
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'处理失败: {str(e)}'})

@bp.route('/clear_emails', methods=['POST'])
def clear_emails():
    """清空邮件列表"""
    try:
        db_path = current_app.config['DATABASE_PATH']

        # 删除所有邮件记录
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        # 先删除所有发票记录（因为有外键约束）
        cursor.execute('DELETE FROM invoices')
        deleted_invoices = cursor.rowcount

        # 再删除所有邮件记录
        cursor.execute('DELETE FROM emails')
        deleted_emails = cursor.rowcount

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'已清空 {deleted_emails} 封邮件和 {deleted_invoices} 张发票记录'
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'清空失败: {str(e)}'})
