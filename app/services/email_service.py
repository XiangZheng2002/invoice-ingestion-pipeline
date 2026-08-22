import imaplib
import email
import socket
from email.header import decode_header
from email.utils import parsedate_to_datetime
import os
from app.utils.validators import Validators
from app.services import mail_providers

class EmailService:
    """邮件服务类 - 通用IMAP连接与邮件读取，服务商差异见 mail_providers"""

    CONNECT_TIMEOUT = 30

    def __init__(self, provider_key=None, imap_host=None, imap_port=None):
        self.provider_key = provider_key
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.provider = None
        self.imap_server = imap_host        # 兼容旧属性名
        self.connection = None
        self.current_folder = 'INBOX'

    def connect(self, email_address, password, provider_key=None,
                imap_host=None, imap_port=None):
        """
        连接邮箱

        服务器参数优先级：本次调用传入 > 构造时传入 > 按邮箱域名自动识别
        """
        if not Validators.is_valid_email(email_address):
            return False, "邮箱格式不正确"

        provider, host, port = mail_providers.resolve(
            email_address=email_address,
            provider_key=provider_key or self.provider_key,
            imap_host=imap_host or self.imap_host,
            imap_port=imap_port or self.imap_port,
        )
        self.provider = provider
        self.imap_host = self.imap_server = host
        self.imap_port = port

        if not host:
            return False, "无法识别该邮箱的 IMAP 服务器，请在设置里手动填写服务器地址"

        try:
            self.connection = imaplib.IMAP4_SSL(host, port, timeout=self.CONNECT_TIMEOUT)
            self.connection.login(email_address, password)

            # 163/126/yeah 登录后必须先发 IMAP ID，否则后续操作全部被拒
            if provider.needs_imap_id:
                self._send_imap_id()

            return True, f"连接成功（{provider.name} · {host}）"

        except imaplib.IMAP4.error as e:
            self.disconnect()
            return False, self._explain_imap_error(str(e), provider)

        except socket.gaierror:
            self.disconnect()
            return False, f"找不到服务器 {host}，请检查 IMAP 地址是否正确"

        except (socket.timeout, TimeoutError):
            self.disconnect()
            return False, f"连接 {host}:{port} 超时，请检查网络或防火墙"

        except OSError as e:
            self.disconnect()
            return False, f"网络错误: {e}"

        except Exception as e:
            self.disconnect()
            return False, f"连接失败: {e}"

    def _send_imap_id(self):
        """
        发送 IMAP ID 指令（RFC 2971）

        网易系（163/126/yeah）要求客户端登录后先自报家门，
        否则 SELECT/SEARCH 会返回 "Unsafe Login. Please contact kefu@188.com"。
        imaplib 默认不认识 ID 命令，需要先注册它允许的状态。
        """
        try:
            imaplib.Commands['ID'] = ('AUTH', 'SELECTED')
            fields = ('name', 'bill-invoice', 'version', '1.0.0',
                      'vendor', 'bill-invoice', 'contact', '')
            payload = '("' + '" "'.join(fields) + '")'
            self.connection._simple_command('ID', payload)
            self.connection._untagged_response('OK', [None], 'ID')
        except Exception as e:
            # 发不出去不致命，真正失败会在后续操作里报出来
            print(f"发送 IMAP ID 失败（网易邮箱可能拒绝后续操作）: {e}")

    def _explain_imap_error(self, error_msg, provider):
        """把 IMAP 的原始报错翻译成用户能照着做的提示"""
        low = error_msg.lower()

        if 'unsafe login' in low:
            return ('网易邮箱拒绝了本次登录。请确认已在邮箱设置里开启 IMAP 服务，'
                    '并且填的是授权码而不是登录密码。')

        # QQ 返回的是 "Login fail."（没有 ed），用 'login fail' 才能同时覆盖两种写法
        if 'authenticationfailed' in low.replace(' ', '') or 'authentication failed' in low \
                or 'login fail' in low or 'invalid credentials' in low \
                or 'service is not open' in low:
            hint = f'请检查邮箱地址和{provider.credential_label}是否正确'
            if provider.key == 'gmail':
                hint = ('Gmail 必须使用「应用专用密码」（账号需先开启两步验证），'
                        '普通登录密码无法连接')
            elif provider.key == 'outlook':
                hint = ('微软已停用个人 Outlook 账号的 IMAP 基本认证，密码方式无法连接。'
                        '建议把发票邮件转发到 QQ/163 邮箱，或直接用「上传识别」')
            elif provider.key == 'icloud':
                hint = 'iCloud 必须使用「App 专用密码」，Apple ID 密码无法连接'
            elif provider.credential_label == '授权码':
                hint = (f'请确认邮箱设置里已开启 IMAP 服务，'
                        f'并且填的是{provider.credential_label}而不是登录密码')
            return f'认证失败：{hint}'

        if 'imap' in low and ('disabled' in low or 'not enabled' in low):
            return f'该账号未开启 IMAP 服务，请先到 {provider.name} 的设置里开启'

        return f'IMAP错误: {error_msg}'

    def disconnect(self):
        """断开连接"""
        if self.connection:
            try:
                self.connection.logout()
            except:
                pass
            self.connection = None

    @staticmethod
    def _quote_folder(folder):
        """
        文件夹名带空格或特殊字符时必须加引号

        imaplib 的 select() 不会自动处理，Gmail 的 "[Gmail]/All Mail"
        直接传进去会被解析成多个参数而失败。
        """
        if not folder:
            return 'INBOX'
        if folder.startswith('"') and folder.endswith('"'):
            return folder
        if any(ch in folder for ch in ' []()"\\{'):
            escaped = folder.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped}"'
        return folder

    def list_folders(self):
        """
        列出账号里的所有文件夹

        Gmail 尤其需要：它把归档邮件移出 INBOX 打上标签，
        只搜 INBOX 很可能一封发票都找不到，得让用户选 [Gmail]/All Mail。
        """
        if not self.connection:
            raise Exception("未连接到邮箱")

        status, data = self.connection.list()
        if status != 'OK':
            return []

        folders = []
        for raw in data:
            if not raw:
                continue
            line = raw.decode('utf-8', errors='ignore') if isinstance(raw, bytes) else str(raw)

            # 形如：(\HasNoChildren) "/" "INBOX"  —— 取最后一段带引号的名字
            if '"' in line:
                name = line.split('"')[-2] if line.rstrip().endswith('"') else line.split('"')[-1]
            else:
                name = line.split()[-1]

            name = name.strip().strip('"')
            if name and name not in folders:
                folders.append(name)

        return folders

    def fetch_emails(self, since_date=None, before_date=None, folder='INBOX'):
        """获取指定日期范围的邮件"""
        if not self.connection:
            raise Exception("未连接到邮箱")

        try:
            # 选择文件夹
            status, _ = self.connection.select(self._quote_folder(folder))
            if status != 'OK':
                print(f"选择文件夹失败: {folder}")
                return []
            self.current_folder = folder

            # 构建IMAP搜索命令
            search_parts = []

            if since_date:
                # IMAP格式: DD-MMM-YYYY (例如: 01-Dec-2024)
                search_parts.append(f'SINCE {since_date.strftime("%d-%b-%Y")}')

            if before_date:
                search_parts.append(f'BEFORE {before_date.strftime("%d-%b-%Y")}')

            # 如果没有指定任何条件，搜索所有邮件
            if search_parts:
                search_criteria = ' '.join(search_parts)
            else:
                search_criteria = 'ALL'

            print(f"IMAP搜索条件: {search_criteria}")

            # 搜索邮件
            status, messages = self.connection.search(None, search_criteria)

            if status != 'OK':
                print(f"搜索失败: {status}")
                return []

            # 获取邮件ID列表
            email_ids = messages[0].split()

            print(f"IMAP返回邮件数量: {len(email_ids)}")

            # 部分服务商（QQ 尤其明显）的 SINCE/BEFORE 过滤不准，客户端再筛一遍兜底
            if since_date or before_date:
                filtered_ids = []
                for email_id in email_ids:
                    try:
                        # 获取邮件日期
                        status, msg_data = self.connection.fetch(email_id, '(INTERNALDATE)')
                        if status == 'OK':
                            # 解析INTERNALDATE
                            import email.utils
                            date_str = msg_data[0].decode('utf-8', errors='ignore')
                            # 从响应中提取日期
                            import re
                            date_match = re.search(r'INTERNALDATE "([^"]+)"', date_str)
                            if date_match:
                                date_tuple = email.utils.parsedate(date_match.group(1))
                                if date_tuple:
                                    from datetime import datetime
                                    email_date = datetime(*date_tuple[:6])

                                    # 检查日期范围
                                    if since_date and email_date.date() < since_date.date():
                                        continue
                                    if before_date and email_date.date() >= before_date.date():
                                        continue

                                    filtered_ids.append(email_id)
                    except Exception as e:
                        print(f"过滤邮件时出错 {email_id}: {e}")
                        # 如果出错，保守地包含这封邮件
                        filtered_ids.append(email_id)

                print(f"客户端过滤后邮件数量: {len(filtered_ids)}")
                return filtered_ids
            else:
                return email_ids

        except Exception as e:
            print(f"获取邮件列表失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def parse_email(self, email_id):
        """解析邮件内容"""
        if not self.connection:
            raise Exception("未连接到邮箱")

        try:
            # 确保已选择邮箱文件夹（IMAP必须处于SELECTED状态才能FETCH）
            # 注意要重选当前文件夹，不能写死 INBOX ——
            # Gmail 用户可能选的是 [Gmail]/All Mail，重选 INBOX 会导致邮件ID对不上
            try:
                if self.connection.state != 'SELECTED':
                    self.connection.select(self._quote_folder(self.current_folder))
            except Exception:
                self.connection.select(self._quote_folder(self.current_folder))

            # 获取邮件数据
            status, msg_data = self.connection.fetch(email_id, '(RFC822)')

            if status != 'OK':
                raise Exception(f"获取邮件失败: {status}")

            # 解析邮件
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)

            # 解析主题
            subject = self._decode_header(email_message['Subject'])

            # 解析发件人
            from_ = self._decode_header(email_message.get('From', ''))

            # 解析日期
            date_str = email_message.get('Date')
            try:
                received_date = parsedate_to_datetime(date_str)
            except:
                from datetime import datetime
                received_date = datetime.now()

            # 解析正文和附件
            body = ""
            attachments = []

            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition', ''))

                    # 获取正文
                    if content_type == "text/plain" and 'attachment' not in content_disposition:
                        try:
                            payload = part.get_payload(decode=True)
                            charset = part.get_content_charset() or 'utf-8'
                            body += payload.decode(charset, errors='ignore')
                        except:
                            pass

                    # 获取附件
                    elif 'attachment' in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            filename = self._decode_header(filename)
                            attachments.append({
                                'filename': filename,
                                'data': part.get_payload(decode=True),
                                'content_type': content_type
                            })
            else:
                # 非multipart邮件
                try:
                    payload = email_message.get_payload(decode=True)
                    charset = email_message.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='ignore')
                except:
                    body = ""

            return {
                'email_id': email_id.decode() if isinstance(email_id, bytes) else str(email_id),
                'subject': subject,
                'sender': from_,
                'received_date': received_date.strftime('%Y-%m-%d %H:%M:%S'),
                'body': body,
                'attachments': attachments
            }

        except Exception as e:
            print(f"解析邮件失败 {email_id}: {e}")
            raise

    def download_attachment(self, attachment, save_path):
        """保存附件到本地"""
        try:
            # 清理文件名
            filename = Validators.sanitize_filename(attachment['filename'])
            filepath = os.path.join(save_path, filename)

            # 确保目录存在
            os.makedirs(save_path, exist_ok=True)

            # 写入文件
            with open(filepath, 'wb') as f:
                f.write(attachment['data'])

            return filepath

        except Exception as e:
            print(f"保存附件失败: {e}")
            return None

    def _decode_header(self, header_value):
        """解码邮件头"""
        if not header_value:
            return ""

        decoded_parts = decode_header(header_value)
        decoded_string = ""

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    if encoding:
                        decoded_string += part.decode(encoding)
                    else:
                        # 尝试常见编码
                        for enc in ['utf-8', 'gb2312', 'gbk', 'gb18030']:
                            try:
                                decoded_string += part.decode(enc)
                                break
                            except:
                                continue
                        else:
                            decoded_string += part.decode('utf-8', errors='ignore')
                except:
                    decoded_string += part.decode('utf-8', errors='ignore')
            else:
                decoded_string += str(part)

        return decoded_string

    def __del__(self):
        """析构函数 - 确保连接关闭"""
        self.disconnect()
