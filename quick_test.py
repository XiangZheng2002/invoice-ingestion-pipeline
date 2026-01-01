#!/usr/bin/env python3
"""快速测试日期筛选（只测试前100封）"""

import sys
sys.path.insert(0, '/Users/zhengxiang/Documents/ZLiang/bill')

from app.services.email_service import EmailService
from datetime import datetime, timedelta
import imaplib

email_address = "1793434271@qq.com"
password = "vrhhqgruvomtfjjf"

print("=" * 70)
print("快速测试日期筛选功能")
print("=" * 70)

# 直接使用IMAP测试
connection = imaplib.IMAP4_SSL('imap.qq.com', 993)
connection.login(email_address, password)
connection.select('INBOX')

# 测试：获取2024年12月的邮件
since_date = datetime(2024, 12, 1)
before_date = datetime(2024, 12, 29)

print(f"\n测试日期范围: {since_date.date()} 到 {before_date.date()}")
print("-" * 70)

# IMAP搜索
search_criteria = f'SINCE {since_date.strftime("%d-%b-%Y")} BEFORE {before_date.strftime("%d-%b-%Y")}'
print(f"IMAP搜索命令: {search_criteria}")

status, messages = connection.search(None, search_criteria)
all_ids = messages[0].split()
print(f"IMAP返回数量: {len(all_ids)}")

# 手动验证前20封邮件的日期
print(f"\n验证前20封邮件的实际日期:")
print("-" * 70)

valid_count = 0
invalid_count = 0

for i, email_id in enumerate(all_ids[:20]):
    status, msg_data = connection.fetch(email_id, '(INTERNALDATE)')
    if status == 'OK':
        import re
        import email.utils
        date_str = msg_data[0].decode('utf-8', errors='ignore')
        date_match = re.search(r'INTERNALDATE "([^"]+)"', date_str)
        if date_match:
            date_tuple = email.utils.parsedate(date_match.group(1))
            if date_tuple:
                email_date = datetime(*date_tuple[:6])
                in_range = since_date.date() <= email_date.date() < before_date.date()

                status_icon = "✅" if in_range else "❌"
                print(f"{status_icon} {i+1}. {email_date.date()}")

                if in_range:
                    valid_count += 1
                else:
                    invalid_count += 1

connection.logout()

print("\n" + "=" * 70)
print(f"验证结果: {valid_count}封在范围内, {invalid_count}封不在范围内")
if invalid_count > 0:
    print("⚠️  QQ邮箱IMAP的SINCE/BEFORE命令不可靠，需要客户端过滤")
else:
    print("✅ IMAP过滤正常工作")
print("=" * 70)
