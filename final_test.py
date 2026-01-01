#!/usr/bin/env python3
"""完整端到端测试"""

import requests
import json
import re

BASE_URL = "http://127.0.0.1:5000"
session = requests.Session()

print("=" * 70)
print("完整端到端测试 - 起始和终止日期")
print("=" * 70)

# 获取CSRF token
response = session.get(f"{BASE_URL}/config")
csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', response.text)
csrf_token = csrf_match.group(1) if csrf_match else None

headers = {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrf_token
}

# 测试1: 保存配置（带起始和终止日期）
print("\n1. 保存配置（2024-12-01 到 2024-12-15）")
print("-" * 70)

data = {
    'email': '1793434271@qq.com',
    'password': 'vrhhqgruvomtfjjf',
    'since_date': '2024-12-01',
    'before_date': '2024-12-15'
}

response = session.post(
    f"{BASE_URL}/email/save_config",
    headers=headers,
    data=json.dumps(data)
)

result = response.json()
if result.get('success'):
    print(f"✅ {result.get('message')}")
else:
    print(f"❌ {result.get('message')}")
    exit(1)

# 测试2: 清空旧数据
print("\n2. 清空现有邮件数据")
print("-" * 70)

response = session.post(
    f"{BASE_URL}/email/clear_emails",
    headers=headers,
    data=json.dumps({})
)

result = response.json()
if result.get('success'):
    print(f"✅ {result.get('message')}")
else:
    print(f"⚠️  {result.get('message')}")

# 测试3: 获取邮件（应该使用配置的日期范围）
print("\n3. 获取邮件（自动使用配置的日期范围）")
print("-" * 70)

response = session.post(
    f"{BASE_URL}/email/fetch_emails",
    headers=headers,
    data=json.dumps({})
)

result = response.json()
if result.get('success'):
    print(f"✅ {result.get('message')}")
    count = result.get('count')
    print(f"   获取数量: {count} 封")

    if count > 0:
        print(f"\n   预期: 应该只获取2024年12月1日到14日的邮件")
        print(f"   实际: 成功获取{count}封邮件")
    else:
        print("   ⚠️  没有获取到邮件，可能该时间段没有邮件")
else:
    print(f"❌ {result.get('message')}")

# 测试4: 测试不设置终止日期
print("\n\n4. 测试只设置起始日期（获取到最新）")
print("-" * 70)

data = {
    'email': '1793434271@qq.com',
    'password': 'vrhhqgruvomtfjjf',
    'since_date': '2024-12-25',
    'before_date': ''  # 不设置终止日期
}

response = session.post(
    f"{BASE_URL}/email/save_config",
    headers=headers,
    data=json.dumps(data)
)

result = response.json()
if result.get('success'):
    print(f"✅ 配置保存成功（起始: 2024-12-25, 终止: 最新）")
else:
    print(f"❌ {result.get('message')}")

print("\n" + "=" * 70)
print("测试完成！")
print("=" * 70)
print("\n现在你可以:")
print("1. 访问 http://127.0.0.1:5000/config 配置日期范围")
print("2. 访问 http://127.0.0.1:5000/email/list 查看获取的邮件")
print("3. 邮件列表会显示: '日期范围: 2024-12-25 至 最新'")
