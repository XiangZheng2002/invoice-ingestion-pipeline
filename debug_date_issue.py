#!/usr/bin/env python3
"""调试日期问题"""

import sys
sys.path.insert(0, '/Users/zhengxiang/Documents/ZLiang/bill')

from app.services.email_service import EmailService
from datetime import datetime

# 测试连接
email_address = "1793434271@qq.com"
password = "vrhhqgruvomtfjjf"

print("=" * 70)
print("调试邮件日期筛选问题")
print("=" * 70)

email_service = EmailService()
success, message = email_service.connect(email_address, password)

if not success:
    print(f"连接失败: {message}")
    sys.exit(1)

print(f"✅ 连接成功\n")

# 测试不同的日期
test_dates = [
    "2024-12-01",
    "2024-12-25",
    "2024-12-28",
    "2025-01-01",
]

for date_str in test_dates:
    since_date = datetime.strptime(date_str, '%Y-%m-%d')

    print(f"\n测试日期: {date_str}")
    print(f"IMAP格式: {since_date.strftime('%d-%b-%Y')}")
    print("-" * 70)

    email_ids = email_service.fetch_emails(since_date)
    print(f"找到邮件数量: {len(email_ids)}")

    # 解析前5封邮件看日期
    if len(email_ids) > 0:
        print("\n前5封邮件的日期:")
        for i, email_id in enumerate(email_ids[:5]):
            try:
                email_data = email_service.parse_email(email_id)
                print(f"  {i+1}. {email_data['received_date'][:10]} - {email_data['subject'][:50]}")
            except Exception as e:
                print(f"  {i+1}. 解析失败: {e}")

email_service.disconnect()

print("\n" + "=" * 70)
print("调试完成")
print("=" * 70)
