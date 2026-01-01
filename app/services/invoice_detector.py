"""
发票检测器
用于识别邮件是否包含发票，以及发票的类型
"""

class InvoiceDetector:
    """发票检测器类"""

    # 发票关键词（中英文）
    INVOICE_KEYWORDS = [
        '发票', 'invoice', '报销', '增值税',
        '专用发票', '普通发票', '电子发票',
        '发票查验', '税务', 'fapiao',
        '开票', '发票信息', '发票通知'
    ]

    # 常见发票发件人域名
    INVOICE_SENDER_DOMAINS = [
        'alipay.com',          # 支付宝
        'tenpay.com',          # 微信支付
        'jd.com',              # 京东
        'taobao.com',          # 淘宝
        'tmall.com',           # 天猫
        'meituan.com',         # 美团
        'ctrip.com',           # 携程
        'didi.com',            # 滴滴
        'eleme.me',            # 饿了么
        '12306.cn',            # 12306
        'suning.com',          # 苏宁
        'vip.com',             # 唯品会
        '163.com',             # 网易
        'qq.com',              # 腾讯
        'invoice',             # 包含invoice的域名
        'fapiao',              # 包含fapiao的域名
        'billing'              # 包含billing的域名
    ]

    # 发票相关文件名关键词
    INVOICE_FILENAME_KEYWORDS = [
        '发票', 'invoice', 'fapiao',
        '报销', 'billing', '账单',
        '税务', 'tax'
    ]

    def __init__(self):
        pass

    def is_invoice_email(self, email_data):
        """
        判断邮件是否为发票邮件

        Args:
            email_data: 邮件数据字典，包含subject, sender, body, attachments

        Returns:
            bool: 是否为发票邮件
        """
        # 检查主题
        subject = email_data.get('subject', '').lower()
        if self._contains_keywords(subject, self.INVOICE_KEYWORDS):
            return True

        # 检查发件人
        sender = email_data.get('sender', '').lower()
        if self._check_sender(sender):
            # 如果发件人是已知的发票来源，进一步检查附件
            attachments = email_data.get('attachments', [])
            if attachments:
                # 只要有附件就认为可能是发票
                for att in attachments:
                    filename = att.get('filename', '').lower()
                    if filename.endswith(('.pdf', '.jpg', '.jpeg', '.png', '.bmp')):
                        return True

        # 检查正文
        body = email_data.get('body', '').lower()
        if self._contains_keywords(body, self.INVOICE_KEYWORDS):
            # 正文包含关键词，但需要进一步验证
            # 避免误判（如营销邮件提到发票）
            if '发票' in body or 'invoice' in body:
                return True

        # 检查附件（宽松模式：只要有PDF或图片附件就可能是发票）
        attachments = email_data.get('attachments', [])
        if self._check_attachments_relaxed(attachments):
            return True

        return False

    def detect_invoice_type(self, email_data):
        """
        检测发票类型

        Args:
            email_data: 邮件数据字典

        Returns:
            list: 发票类型列表 ['PDF附件', '图片附件', '电子发票链接']
        """
        types = []

        # 检查附件
        attachments = email_data.get('attachments', [])
        for att in attachments:
            filename = att.get('filename', '').lower()

            if filename.endswith('.pdf'):
                if self._contains_keywords(filename, self.INVOICE_FILENAME_KEYWORDS):
                    types.append('PDF附件')

            elif filename.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif')):
                if self._contains_keywords(filename, self.INVOICE_FILENAME_KEYWORDS):
                    types.append('图片附件')

        # 检查正文链接
        body = email_data.get('body', '')
        if self._contains_invoice_links(body):
            types.append('电子发票链接')

        # 如果正文中直接包含发票信息
        if self._contains_invoice_text(body):
            types.append('邮件正文')

        return types if types else ['未知']

    def extract_invoice_files(self, email_data):
        """
        提取发票相关的附件

        Args:
            email_data: 邮件数据字典

        Returns:
            list: 发票附件列表
        """
        invoice_attachments = []
        attachments = email_data.get('attachments', [])

        for att in attachments:
            filename = att.get('filename', '').lower()

            # 检查文件格式和文件名
            is_valid_format = filename.endswith(('.pdf', '.jpg', '.jpeg', '.png', '.bmp'))
            is_invoice_name = self._contains_keywords(filename, self.INVOICE_FILENAME_KEYWORDS)

            # 优先级1：文件名包含发票关键词且格式正确
            if is_valid_format and is_invoice_name:
                invoice_attachments.append(att)
            # 优先级2：PDF文件（很可能是发票）
            elif filename.endswith('.pdf'):
                invoice_attachments.append(att)
            # 优先级3：只有1-2个附件且是图片格式
            elif is_valid_format and len(attachments) <= 2:
                invoice_attachments.append(att)

        return invoice_attachments

    def _contains_keywords(self, text, keywords):
        """检查文本是否包含关键词"""
        if not text:
            return False

        text = text.lower()
        return any(keyword.lower() in text for keyword in keywords)

    def _check_sender(self, sender):
        """检查发件人是否为常见发票发送方"""
        if not sender:
            return False

        sender = sender.lower()
        return any(domain in sender for domain in self.INVOICE_SENDER_DOMAINS)

    def _check_attachments(self, attachments):
        """检查附件是否包含发票文件（严格模式：文件名必须包含关键词）"""
        if not attachments:
            return False

        for att in attachments:
            filename = att.get('filename', '').lower()

            # 检查文件名是否包含发票关键词
            if self._contains_keywords(filename, self.INVOICE_FILENAME_KEYWORDS):
                # 检查文件格式
                if filename.endswith(('.pdf', '.jpg', '.jpeg', '.png', '.bmp')):
                    return True

        return False

    def _check_attachments_relaxed(self, attachments):
        """检查附件是否包含发票文件（宽松模式：只要有PDF或图片即可）"""
        if not attachments:
            return False

        for att in attachments:
            filename = att.get('filename', '').lower()

            # 先检查是否有明确的发票关键词
            if self._contains_keywords(filename, self.INVOICE_FILENAME_KEYWORDS):
                if filename.endswith(('.pdf', '.jpg', '.jpeg', '.png', '.bmp')):
                    return True

            # 宽松模式：如果有PDF或常见图片格式，也认为可能是发票
            # 但排除一些明显不是发票的文件名
            exclude_keywords = ['logo', 'banner', 'signature', '签名', '头像', 'avatar']
            is_excluded = any(kw in filename for kw in exclude_keywords)

            if not is_excluded:
                if filename.endswith('.pdf'):
                    return True
                # 对于图片，如果只有1个附件，也认为可能是发票
                elif filename.endswith(('.jpg', '.jpeg', '.png', '.bmp')) and len(attachments) <= 2:
                    return True

        return False

    def _contains_invoice_links(self, body):
        """检查正文是否包含发票下载链接"""
        if not body:
            return False

        body_lower = body.lower()

        # 检查是否包含链接和发票相关词
        has_link = 'http' in body_lower or 'www.' in body_lower
        has_invoice_word = any(keyword in body_lower for keyword in ['发票', 'invoice', 'fapiao'])
        has_download_word = any(word in body_lower for word in ['下载', 'download', '查看', 'view', '点击', 'click'])

        return has_link and has_invoice_word and has_download_word

    def _contains_invoice_text(self, body):
        """检查正文是否直接包含发票信息（如发票号码）"""
        if not body:
            return False

        body_lower = body.lower()

        # 检查是否包含发票号码、金额等关键信息
        indicators = [
            '发票号码' in body_lower or '发票代码' in body_lower,
            '价税合计' in body_lower or '税额' in body_lower,
            '购买方' in body_lower or '销售方' in body_lower
        ]

        return any(indicators)

    def get_detection_confidence(self, email_data):
        """
        获取发票检测的置信度

        Args:
            email_data: 邮件数据字典

        Returns:
            float: 置信度 0-1
        """
        score = 0.0

        subject = email_data.get('subject', '').lower()
        sender = email_data.get('sender', '').lower()
        body = email_data.get('body', '').lower()
        attachments = email_data.get('attachments', [])

        # 主题包含发票 +30分
        if '发票' in subject or 'invoice' in subject:
            score += 0.3

        # 发件人是已知发票来源 +25分
        if self._check_sender(sender):
            score += 0.25

        # 有发票附件 +30分
        if self._check_attachments(attachments):
            score += 0.3

        # 正文包含发票信息 +15分
        if '发票号码' in body or '发票代码' in body:
            score += 0.15

        return min(score, 1.0)
