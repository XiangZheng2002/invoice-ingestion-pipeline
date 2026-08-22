#!/usr/bin/env python3
"""
多邮箱支持测试

不连真实邮箱服务器，用假的 IMAP 连接验证：
  - 按域名识别服务商
  - 连接参数的优先级（显式 > 指定服务商 > 域名识别）
  - 163 系登录后是否发了 IMAP ID（不发的话后续操作会被拒）
  - 文件夹名的引号处理（Gmail 的 [Gmail]/All Mail 带空格）
  - 各家认证失败时的提示是否对症

用法：
    python test_mail_providers.py
"""

import os
import sys

for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, 'reconfigure'):
        try:
            _stream.reconfigure(encoding='utf-8', errors='replace')
        except (ValueError, OSError):
            pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import imaplib

from app.services import mail_providers
from app.services.email_service import EmailService

failures = []


def check(label, got, want):
    ok = got == want
    print(f"  {'✓' if ok else '✗'} {label}: {got!r}" + ('' if ok else f'   (期望 {want!r})'))
    if not ok:
        failures.append(label)


def check_true(label, cond, detail=''):
    print(f"  {'✓' if cond else '✗'} {label}" + ('' if cond else f'   {detail}'))
    if not cond:
        failures.append(label)


class FakeIMAP:
    """假的 IMAP4_SSL，记录收到的指令"""

    instances = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.state = 'NONAUTH'
        self.commands = []
        self.login_error = None
        FakeIMAP.instances.append(self)

    def login(self, user, password):
        self.commands.append(('LOGIN', user))
        if self.login_error:
            raise imaplib.IMAP4.error(self.login_error)
        self.state = 'AUTH'
        return 'OK', [b'']

    def _simple_command(self, name, *args):
        self.commands.append((name,) + args)
        return 'OK', [b'']

    def _untagged_response(self, typ, dat, name):
        return typ, dat

    def select(self, mailbox='INBOX'):
        self.commands.append(('SELECT', mailbox))
        self.state = 'SELECTED'
        return 'OK', [b'1']

    def list(self):
        return 'OK', [
            b'(\\HasNoChildren) "/" "INBOX"',
            b'(\\HasNoChildren \\All) "/" "[Gmail]/All Mail"',
            b'(\\HasNoChildren \\Sent) "/" "[Gmail]/Sent Mail"',
        ]

    def logout(self):
        self.state = 'LOGOUT'
        return 'BYE', [b'']


def with_fake_imap(fn):
    """替换 imaplib.IMAP4_SSL 跑一段逻辑"""
    original = imaplib.IMAP4_SSL
    FakeIMAP.instances = []
    imaplib.IMAP4_SSL = FakeIMAP
    try:
        return fn()
    finally:
        imaplib.IMAP4_SSL = original


def test_detect():
    print('\n=== 按域名识别服务商 ===')
    cases = [
        ('someone@qq.com', 'qq'),
        ('someone@foxmail.com', 'qq'),
        ('someone@163.com', '163'),
        ('someone@126.com', '126'),
        ('someone@yeah.net', 'yeah'),
        ('someone@gmail.com', 'gmail'),
        ('SomeOne@GMail.COM', 'gmail'),          # 大小写不敏感
        ('someone@outlook.com', 'outlook'),
        ('someone@hotmail.com', 'outlook'),
        ('someone@icloud.com', 'icloud'),
        ('someone@sina.com', 'sina'),
        ('someone@aliyun.com', 'aliyun'),
        ('someone@139.com', '139'),
    ]
    for addr, want in cases:
        p = mail_providers.detect(addr)
        check(addr, p.key if p else None, want)

    check('不认识的域名', mail_providers.detect('a@example.com'), None)
    check('非法地址', mail_providers.detect('not-an-email'), None)


def test_resolve_priority():
    print('\n=== 连接参数优先级 ===')
    _, host, port = mail_providers.resolve(email_address='a@163.com')
    check('域名识别', f'{host}:{port}', 'imap.163.com:993')

    _, host, port = mail_providers.resolve(email_address='a@163.com', provider_key='qq')
    check('显式服务商覆盖域名', f'{host}:{port}', 'imap.qq.com:993')

    _, host, port = mail_providers.resolve(
        email_address='a@163.com', imap_host='mail.corp.com', imap_port='1993')
    check('显式服务器覆盖一切', f'{host}:{port}', 'mail.corp.com:1993')

    p, host, port = mail_providers.resolve(email_address='a@example.com')
    check('未知域名落到 custom', p.key, 'custom')
    check('custom 无默认服务器', host, '')

    _, host, port = mail_providers.resolve(email_address='a@qq.com', imap_port='abc')
    check('端口非法时回退默认', port, 993)


def test_imap_id():
    print('\n=== 163 系必须发 IMAP ID ===')

    def run_163():
        svc = EmailService()
        ok, msg = svc.connect('someone@163.com', 'authcode')
        return svc, ok, msg

    svc, ok, msg = with_fake_imap(run_163)
    check_true('163 连接成功', ok, msg)
    conn = FakeIMAP.instances[0]
    check('连到 163 服务器', f'{conn.host}:{conn.port}', 'imap.163.com:993')
    sent = [c[0] for c in conn.commands]
    check_true('登录后发了 ID 指令', 'ID' in sent, f'实际指令: {sent}')
    id_payload = next((c[1] for c in conn.commands if c[0] == 'ID'), '')
    check_true('ID 内容格式正确', id_payload.startswith('("name"'), id_payload)

    def run_qq():
        svc = EmailService()
        svc.connect('someone@qq.com', 'authcode')
        return svc

    with_fake_imap(run_qq)
    sent = [c[0] for c in FakeIMAP.instances[0].commands]
    check_true('QQ 不发 ID 指令', 'ID' not in sent, f'实际指令: {sent}')


def test_folder_quoting():
    print('\n=== 文件夹名引号处理 ===')
    q = EmailService._quote_folder
    check('普通名不加引号', q('INBOX'), 'INBOX')
    check('带空格要加引号', q('[Gmail]/All Mail'), '"[Gmail]/All Mail"')
    check('带方括号要加引号', q('[Gmail]/Spam'), '"[Gmail]/Spam"')
    check('已有引号不重复加', q('"已发送"'), '"已发送"')
    check('空值回退 INBOX', q(''), 'INBOX')
    check('转义内部引号', q('a"b'), '"a\\"b"')


def test_list_folders():
    print('\n=== 列出文件夹 ===')

    def run():
        svc = EmailService()
        svc.connect('someone@gmail.com', 'app-password')
        return svc.list_folders()

    folders = with_fake_imap(run)
    check('解析出 3 个文件夹', len(folders), 3)
    check_true('含 INBOX', 'INBOX' in folders, str(folders))
    check_true('含带空格的 Gmail 文件夹', '[Gmail]/All Mail' in folders, str(folders))


def test_error_messages():
    print('\n=== 认证失败提示是否对症 ===')

    def make_failing(addr, error):
        def run():
            original = imaplib.IMAP4_SSL

            def factory(host, port, timeout=None):
                conn = FakeIMAP(host, port, timeout)
                conn.login_error = error
                return conn

            imaplib.IMAP4_SSL = factory
            try:
                return EmailService().connect(addr, 'wrong')
            finally:
                imaplib.IMAP4_SSL = original
        FakeIMAP.instances = []
        return run()

    ok, msg = make_failing('a@gmail.com', b'[AUTHENTICATIONFAILED] Invalid credentials')
    check_true('Gmail 提示应用专用密码', not ok and '应用专用密码' in msg, msg)

    ok, msg = make_failing('a@outlook.com', b'LOGIN failed')
    check_true('Outlook 提示基本认证已停用', not ok and '基本认证' in msg, msg)

    ok, msg = make_failing('a@163.com', b'Unsafe Login. Please contact kefu@188.com')
    check_true('163 提示开启 IMAP 和用授权码', not ok and 'IMAP' in msg and '授权码' in msg, msg)

    ok, msg = make_failing('a@qq.com', b'authentication failed')
    check_true('QQ 提示授权码', not ok and '授权码' in msg, msg)

    # QQ 真实返回的是 "Login fail."，没有 ed，容易漏匹配
    qq_real = (b'Login fail. Account is abnormal, service is not open, '
               b'password is incorrect, login frequency limited, or system is busy.')
    ok, msg = make_failing('a@qq.com', qq_real)
    check_true('QQ 真实报错也能翻译', not ok and '授权码' in msg and 'IMAP' in msg, msg)

    ok, msg = make_failing('a@icloud.com', b'Invalid credentials')
    check_true('iCloud 提示 App 专用密码', not ok and 'App 专用密码' in msg, msg)


def test_custom_without_host():
    print('\n=== 自定义服务商但没填服务器 ===')
    ok, msg = EmailService().connect('a@example.com', 'pw', provider_key='custom')
    check_true('应当拒绝并给出提示', not ok and '手动填写' in msg, msg)


def main():
    test_detect()
    test_resolve_priority()
    test_imap_id()
    test_folder_quoting()
    test_list_folders()
    test_error_messages()
    test_custom_without_host()

    print()
    if failures:
        print(f'✗ {len(failures)} 项未通过: {failures}')
        return 1
    print('✓ 全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
