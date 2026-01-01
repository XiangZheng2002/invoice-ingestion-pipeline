#!/usr/bin/env python3
"""测试邮箱连接"""

import sys
sys.path.insert(0, '/Users/zhengxiang/Documents/ZLiang/bill')

from app.services.email_service import EmailService

# 测试连接
email_address = "1793434271@qq.com"
password = "vrhhqgruvomtfjjf"

print(f"测试连接到邮箱: {email_address}")
print("=" * 60)

email_service = EmailService()
success, message = email_service.connect(email_address, password)

print(f"连接结果: {'成功' if success else '失败'}")
print(f"消息: {message}")
print("=" * 60)

if success:
    print("尝试获取邮件列表...")
    from datetime import datetime, timedelta
    since_date = datetime.now() - timedelta(days=7)

    try:
        email_ids = email_service.fetch_emails(since_date)
        print(f"找到 {len(email_ids)} 封邮件")

        if len(email_ids) > 0:
            print("\n测试解析第一封邮件...")
            first_email = email_service.parse_email(email_ids[0])
            print(f"主题: {first_email['subject']}")
            print(f"发件人: {first_email['sender']}")
            print(f"日期: {first_email['received_date']}")
            print(f"附件数量: {len(first_email['attachments'])}")
    except Exception as e:
        print(f"获取邮件失败: {e}")
        import traceback
        traceback.print_exc()

    email_service.disconnect()
else:
    print("\n请检查:")
    print("1. 邮箱地址是否正确")
    print("2. 授权码是否正确（不是QQ密码）")
    print("3. QQ邮箱是否已开启IMAP服务")
    print("4. 网络连接是否正常")
