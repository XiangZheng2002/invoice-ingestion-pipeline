#!/usr/bin/env python3
"""
邮件发票识别系统
启动入口
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("邮件发票识别系统启动中...")
    print("访问地址: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, host='127.0.0.1', port=5000)
