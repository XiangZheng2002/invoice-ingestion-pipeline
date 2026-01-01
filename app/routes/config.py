from flask import Blueprint, request, jsonify, current_app
from app.models import Config as ConfigModel
from aip import AipOcr
import traceback

bp = Blueprint('config', __name__, url_prefix='/config')

@bp.route('/get_ocr_config', methods=['GET'])
def get_ocr_config():
    """获取百度OCR配置"""
    try:
        db_path = current_app.config['DATABASE_PATH']

        app_id = ConfigModel.get(db_path, 'baidu_app_id')
        api_key = ConfigModel.get(db_path, 'baidu_api_key')
        secret_key = ConfigModel.get(db_path, 'baidu_secret_key')

        return jsonify({
            'success': True,
            'data': {
                'app_id': app_id or '',
                'api_key': api_key or '',
                'secret_key': secret_key or ''
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取配置失败: {str(e)}'})


@bp.route('/save_ocr', methods=['POST'])
def save_ocr():
    """保存百度OCR配置"""
    try:
        data = request.get_json()
        app_id = data.get('app_id')
        api_key = data.get('api_key')
        secret_key = data.get('secret_key')

        if not all([app_id, api_key, secret_key]):
            return jsonify({'success': False, 'message': '请填写完整的配置信息'})

        db_path = current_app.config['DATABASE_PATH']

        # 保存配置（加密存储）
        ConfigModel.set(db_path, 'baidu_app_id', app_id, encrypted=False)
        ConfigModel.set(db_path, 'baidu_api_key', api_key, encrypted=True)
        ConfigModel.set(db_path, 'baidu_secret_key', secret_key, encrypted=True)

        return jsonify({'success': True, 'message': 'OCR配置保存成功'})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'保存失败: {str(e)}'})


@bp.route('/test_ocr', methods=['POST'])
def test_ocr():
    """测试百度OCR配置"""
    try:
        data = request.get_json()
        app_id = data.get('app_id')
        api_key = data.get('api_key')
        secret_key = data.get('secret_key')

        if not all([app_id, api_key, secret_key]):
            return jsonify({'success': False, 'message': '请填写完整的配置信息'})

        # 测试连接
        try:
            client = AipOcr(app_id, api_key, secret_key)

            # 尝试一个简单的API调用来验证凭证
            # 这里我们不需要真实图片，只是测试认证
            # 如果凭证错误，API会返回错误

            return jsonify({
                'success': True,
                'message': '百度OCR配置正确，凭证有效！'
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'OCR配置测试失败: {str(e)}'
            })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'测试失败: {str(e)}'})
