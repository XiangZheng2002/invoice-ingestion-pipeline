"""
邮箱服务商注册表

每家邮箱的 IMAP 地址、凭证叫法、开通步骤和各自的坑都集中在这里，
新增一家只需要往 PROVIDERS 里加一条，不用改 EmailService 和路由。

几个要注意的差异：
  - 国内邮箱普遍用"授权码"而不是登录密码
  - 163/126/yeah 登录后必须先发 IMAP ID 指令，否则任何操作都返回 Unsafe Login
  - Gmail / iCloud 要求账号先开两步验证，再生成"应用专用密码"
  - 微软已停用个人 Outlook 账号的 IMAP 基本认证，密码方式大概率连不上
"""


class MailProvider:
    """一家邮箱服务商的配置"""

    def __init__(self, key, name, domains, imap_host, imap_port=993,
                 credential_label='授权码', help_url=None, steps=None,
                 needs_imap_id=False, warning=None):
        self.key = key
        self.name = name
        self.domains = domains
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.credential_label = credential_label   # 密码输入框叫什么
        self.help_url = help_url
        self.steps = steps or []                   # 怎么拿到凭证
        self.needs_imap_id = needs_imap_id         # 登录后是否要发 IMAP ID
        self.warning = warning                     # 需要提前告知用户的限制

    def to_dict(self):
        return {
            'key': self.key,
            'name': self.name,
            'imap_host': self.imap_host,
            'imap_port': self.imap_port,
            'credential_label': self.credential_label,
            'help_url': self.help_url,
            'steps': self.steps,
            'warning': self.warning,
        }

    def __repr__(self):
        return f'<MailProvider {self.key} {self.imap_host}:{self.imap_port}>'


PROVIDERS = [
    MailProvider(
        key='qq',
        name='QQ邮箱 / Foxmail',
        domains=['qq.com', 'foxmail.com', 'vip.qq.com'],
        imap_host='imap.qq.com',
        credential_label='授权码',
        help_url='https://service.mail.qq.com/detail/0/75',
        steps=[
            '登录 QQ 邮箱网页版',
            '设置 → 账户 → POP3/IMAP/SMTP 服务',
            '开启「IMAP/SMTP服务」，按提示验证',
            '复制生成的授权码（不是 QQ 密码）',
        ],
    ),
    MailProvider(
        key='163',
        name='网易163邮箱',
        domains=['163.com'],
        imap_host='imap.163.com',
        credential_label='授权码',
        needs_imap_id=True,
        help_url='https://help.mail.163.com/faqDetail.do?code=d7a5dc8471cd0c0e8b4b8f4f8e49998b374173cfe9171305fa1ce630d7f67ac2a5feb28b66796d3b',
        steps=[
            '登录 163 邮箱网页版',
            '设置 → POP3/SMTP/IMAP',
            '开启「IMAP/SMTP服务」',
            '按提示完成短信验证，复制授权码（不是登录密码）',
        ],
    ),
    MailProvider(
        key='126',
        name='网易126邮箱',
        domains=['126.com'],
        imap_host='imap.126.com',
        credential_label='授权码',
        needs_imap_id=True,
        steps=[
            '登录 126 邮箱网页版',
            '设置 → POP3/SMTP/IMAP',
            '开启「IMAP/SMTP服务」',
            '按提示完成短信验证，复制授权码（不是登录密码）',
        ],
    ),
    MailProvider(
        key='yeah',
        name='网易yeah.net邮箱',
        domains=['yeah.net'],
        imap_host='imap.yeah.net',
        credential_label='授权码',
        needs_imap_id=True,
        steps=[
            '登录 yeah.net 邮箱网页版',
            '设置 → POP3/SMTP/IMAP，开启 IMAP 服务',
            '完成验证后复制授权码',
        ],
    ),
    MailProvider(
        key='gmail',
        name='Gmail',
        domains=['gmail.com', 'googlemail.com'],
        imap_host='imap.gmail.com',
        credential_label='应用专用密码',
        help_url='https://support.google.com/accounts/answer/185833',
        steps=[
            '账号必须先开启两步验证，否则没有应用专用密码入口',
            '打开 https://myaccount.google.com/apppasswords',
            '生成一个应用专用密码，复制那 16 位字符',
            'Gmail 设置 → 转发和 POP/IMAP → 启用 IMAP',
        ],
        warning='Google 已取消「不够安全的应用」选项，必须用应用专用密码，普通登录密码连不上。',
    ),
    MailProvider(
        key='outlook',
        name='Outlook / Hotmail',
        domains=['outlook.com', 'hotmail.com', 'live.com', 'msn.com'],
        imap_host='outlook.office365.com',
        credential_label='密码',
        help_url='https://support.microsoft.com/office/pop-imap-and-smtp-settings-8361e398-8af4-4e97-b147-6c6c4ac95353',
        steps=[
            '个人账号：微软已停用 IMAP 基本认证，大概率无法连接',
            '企业/学校版 Microsoft 365：需要管理员开启 IMAP 并允许基本认证',
            '如果连不上，建议先把发票邮件转发到 QQ/163 邮箱，或直接用「上传识别」',
        ],
        warning='微软自 2024 年 9 月起停用个人 Outlook 账号的 IMAP 基本认证。'
                '这类账号需要 OAuth2 授权，本程序暂不支持，密码方式很可能连接失败。',
    ),
    MailProvider(
        key='icloud',
        name='iCloud 邮箱',
        domains=['icloud.com', 'me.com', 'mac.com'],
        imap_host='imap.mail.me.com',
        credential_label='应用专用密码',
        help_url='https://support.apple.com/102654',
        steps=[
            'Apple ID 必须已开启双重认证',
            '访问 https://account.apple.com → 登录与安全 → App 专用密码',
            '生成并复制密码',
        ],
        warning='必须使用 App 专用密码，Apple ID 登录密码连不上。',
    ),
    MailProvider(
        key='sina',
        name='新浪邮箱',
        domains=['sina.com', 'sina.cn'],
        imap_host='imap.sina.com',
        credential_label='密码或授权码',
        steps=[
            '登录新浪邮箱网页版',
            '设置 → 客户端 POP/IMAP/SMTP，开启 IMAP 服务',
        ],
    ),
    MailProvider(
        key='aliyun',
        name='阿里云邮箱',
        domains=['aliyun.com'],
        imap_host='imap.aliyun.com',
        credential_label='密码',
        steps=[
            '登录阿里云邮箱网页版',
            '设置 → 账户与安全，确认已开启 IMAP 服务',
        ],
    ),
    MailProvider(
        key='139',
        name='中国移动139邮箱',
        domains=['139.com'],
        imap_host='imap.139.com',
        credential_label='授权码',
        steps=[
            '登录 139 邮箱网页版',
            '设置 → POP3/IMAP/SMTP，开启 IMAP 服务并获取授权码',
        ],
    ),
]

# 用户手填服务器地址的兜底选项
CUSTOM_PROVIDER = MailProvider(
    key='custom',
    name='其他邮箱（手动填写服务器）',
    domains=[],
    imap_host='',
    credential_label='密码或授权码',
    steps=[
        '在邮箱服务商的帮助文档里找到 IMAP 服务器地址',
        '端口通常是 993（SSL）',
        '多数邮箱需要先在设置里开启 IMAP 服务',
    ],
)

_BY_KEY = {p.key: p for p in PROVIDERS}
_BY_KEY[CUSTOM_PROVIDER.key] = CUSTOM_PROVIDER

_BY_DOMAIN = {}
for _p in PROVIDERS:
    for _d in _p.domains:
        _BY_DOMAIN[_d] = _p


def detect(email_address):
    """
    按邮箱域名猜服务商

    Args:
        email_address: 完整邮箱地址

    Returns:
        MailProvider or None: 认不出来时返回 None，由调用方决定是否走自定义
    """
    if not email_address or '@' not in email_address:
        return None
    domain = email_address.rsplit('@', 1)[1].strip().lower()
    return _BY_DOMAIN.get(domain)


def get(key):
    """按 key 取服务商，取不到返回 None"""
    return _BY_KEY.get(key)


def resolve(email_address=None, provider_key=None, imap_host=None, imap_port=None):
    """
    确定最终使用的连接参数

    优先级：显式指定的服务器 > 指定的服务商 > 按域名自动识别

    Returns:
        tuple: (provider, host, port)
    """
    provider = get(provider_key) if provider_key else None
    if provider is None:
        provider = detect(email_address)
    if provider is None:
        provider = CUSTOM_PROVIDER

    host = (imap_host or '').strip() or provider.imap_host
    try:
        port = int(imap_port) if imap_port else provider.imap_port
    except (TypeError, ValueError):
        port = provider.imap_port

    return provider, host, port


def all_providers():
    """给前端用的列表，自定义项排最后"""
    return [p.to_dict() for p in PROVIDERS] + [CUSTOM_PROVIDER.to_dict()]


def domain_map():
    """域名 -> 服务商 key，前端据此在输入邮箱时自动选中"""
    return {domain: p.key for domain, p in _BY_DOMAIN.items()}
