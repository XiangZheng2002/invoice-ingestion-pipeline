"""
加密工具

QQ邮箱授权码、百度OCR密钥都用 Fernet 对称加密后存进数据库，
密钥的存放策略（按优先级）：

  1. 环境变量 ENCRYPTION_KEY —— 兼容老部署，开发时也方便
  2. data/encryption.key 文件 —— 打包分发后的默认方式
  3. 都没有则自动生成并写入 2 的位置

关键点：密钥必须持久化。之前的实现是"没有就临时生成一个并打印出来"，
加密和解密会拿到两把不同的钥匙，存进去的密码再也读不出来。
"""

import os
import stat

from cryptography.fernet import Fernet
from dotenv import load_dotenv

from app.paths import get_data_dir

load_dotenv()

KEY_FILENAME = 'encryption.key'

# 进程内缓存，避免每次加解密都读一次文件
_cached_key = None


def get_key_path():
    """密钥文件路径，可用 ENCRYPTION_KEY_FILE 覆盖"""
    custom = os.getenv('ENCRYPTION_KEY_FILE')
    if custom:
        return os.path.abspath(custom)
    return os.path.join(get_data_dir(), KEY_FILENAME)


def _read_key_file(path):
    try:
        with open(path, 'rb') as f:
            key = f.read().strip()
    except OSError:
        return None

    if not key:
        return None

    try:
        Fernet(key)      # 校验格式，损坏的文件不要静默接受
    except (ValueError, TypeError):
        raise RuntimeError(
            f'密钥文件已损坏: {path}\n'
            '如果你有备份请恢复它；否则删除该文件会生成新密钥，'
            '但数据库中已加密的邮箱授权码和OCR密钥将无法解密，需要重新填写。'
        )
    return key


def _write_key_file(path, key):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(key)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)   # 仅本人可读写
    except OSError:
        pass    # Windows 上可能不支持，不影响功能


def load_or_create_key():
    """
    取得加密密钥，必要时生成并持久化

    Returns:
        bytes: Fernet 密钥
    """
    global _cached_key
    if _cached_key:
        return _cached_key

    # 1. 环境变量优先（老部署和开发环境）
    env_key = os.getenv('ENCRYPTION_KEY')
    if env_key:
        key = env_key.encode() if isinstance(env_key, str) else env_key
        try:
            Fernet(key)
            _cached_key = key
            return key
        except (ValueError, TypeError):
            print('警告: 环境变量 ENCRYPTION_KEY 不是有效的 Fernet 密钥，将改用密钥文件')

    # 2. 密钥文件
    path = get_key_path()
    key = _read_key_file(path)
    if key:
        _cached_key = key
        return key

    # 3. 首次运行，生成并落盘
    key = Fernet.generate_key()
    _write_key_file(path, key)
    print(f'已生成新的加密密钥: {path}')
    print('请连同 data/ 目录一起备份，丢失后已保存的邮箱授权码将无法解密。')

    _cached_key = key
    return key


class CryptoUtil:
    """加密解密工具类"""

    def __init__(self):
        self.cipher = Fernet(load_or_create_key())

    def encrypt(self, plaintext):
        """加密文本"""
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()
        return self.cipher.encrypt(plaintext).decode()

    def decrypt(self, ciphertext):
        """解密文本"""
        if isinstance(ciphertext, str):
            ciphertext = ciphertext.encode()
        return self.cipher.decrypt(ciphertext).decode()

    @staticmethod
    def generate_key():
        """生成新的加密密钥"""
        return Fernet.generate_key().decode()
