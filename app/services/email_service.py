import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import os
from app.utils.validators import Validators

class EmailService:
    """邮件服务类 - 处理QQ邮箱IMAP连接和邮件读取"""

    def __init__(self):
        self.imap_server = 'imap.qq.com'
        self.imap_port = 993
        self.connection = None

    def connect(self, email_address, password):
        """连接QQ邮箱"""
        try:
            # 验证邮箱格式
            if not Validators.is_valid_email(email_address):
                return False, "邮箱格式不正确"

            # 连接IMAP服务器
            self.connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)

            # 登录
            self.connection.login(email_address, password)

            return True, "连接成功"

        except imaplib.IMAP4.error as e:
            error_msg = str(e)
            if 'authentication failed' in error_msg.lower():
                return False, "认证失败，请检查邮箱地址和授权码是否正确"
            return False, f"IMAP错误: {error_msg}"

        except Exception as e:
            return False, f"连接失败: {str(e)}"

    def disconnect(self):
        """断开连接"""
        if self.connection:
            try:
                self.connection.logout()
            except:
                pass
            self.connection = None

    def fetch_emails(self, since_date=None, before_date=None, folder='INBOX'):
        """获取指定日期范围的邮件"""
        if not self.connection:
            raise Exception("未连接到邮箱")

        try:
            # 选择文件夹
            self.connection.select(folder)

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

            # 如果IMAP搜索没有正确过滤（QQ邮箱的bug），在客户端再过滤一次
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
            try:
                # 尝试获取当前状态
                state = self.connection.state
                if state != 'SELECTED':
                    self.connection.select('INBOX')
            except:
                # 如果出错，尝试重新选择INBOX
                self.connection.select('INBOX')

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
