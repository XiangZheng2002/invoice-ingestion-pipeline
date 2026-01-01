#!/usr/bin/env python3
"""测试修复后的日期筛选"""

import sys
sys.path.insert(0, '/Users/zhengxiang/Documents/ZLiang/bill')

from app.services.email_service import EmailService
from datetime import datetime

# 测试连接
email_address = "1793434271@qq.com"
password = "vrhhqgruvomtfjjf"

print("=" * 70)
print("测试修复后的日期筛选功能")
print("=" * 70)

email_service = EmailService()
success, message = email_service.connect(email_address, password)

if not success:
    print(f"连接失败: {message}")
    sys.exit(1)

print(f"✅ 连接成功\n")

# 测试1: 只设置起始日期
print("\n测试1: 起始日期 2024-12-01（获取12月1日到最新的邮件）")
print("=" * 70)
since_date = datetime(2024, 12, 1)
email_ids = email_service.fetch_emails(since_date=since_date)
print(f"找到邮件数量: {len(email_ids)}")

if len(email_ids) > 0:
    print("\n前5封邮件的日期:")
    for i, email_id in enumerate(email_ids[:5]):
        try:
            email_data = email_service.parse_email(email_id)
            print(f"  {i+1}. {email_data['received_date'][:10]} - {email_data['subject'][:50]}")
        except:
            pass

# 测试2: 设置起始和终止日期
print("\n\n测试2: 日期范围 2024-12-01 到 2024-12-15")
print("=" * 70)
since_date = datetime(2024, 12, 1)
before_date = datetime(2024, 12, 15)
email_ids = email_service.fetch_emails(since_date=since_date, before_date=before_date)
print(f"找到邮件数量: {len(email_ids)}")

if len(email_ids) > 0:
    print("\n前5封邮件的日期:")
    for i, email_id in enumerate(email_ids[:5]):
        try:
            email_data = email_service.parse_email(email_id)
            print(f"  {i+1}. {email_data['received_date'][:10]} - {email_data['subject'][:50]}")
        except:
            pass

    print(f"\n最后5封邮件的日期:")
    for i, email_id in enumerate(email_ids[-5:]):
        try:
            email_data = email_service.parse_email(email_id)
            print(f"  {i+1}. {email_data['received_date'][:10]} - {email_data['subject'][:50]}")
        except:
            pass

# 测试3: 最近7天
print("\n\n测试3: 最近7天的邮件")
print("=" * 70)
from datetime import timedelta
since_date = datetime.now() - timedelta(days=7)
email_ids = email_service.fetch_emails(since_date=since_date)
print(f"找到邮件数量: {len(email_ids)}")

if len(email_ids) > 0:
    print("\n所有邮件的日期:")
    for i, email_id in enumerate(email_ids):
        try:
            email_data = email_service.parse_email(email_id)
            print(f"  {i+1}. {email_data['received_date'][:10]} - {email_data['subject'][:50]}")
        except:
            pass

email_service.disconnect()

print("\n" + "=" * 70)
print("测试完成！")
print("=" * 70)
