from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

load_dotenv()

class CryptoUtil:
    """加密解密工具类"""

    def __init__(self):
        # 从环境变量读取密钥
        key = os.getenv('ENCRYPTION_KEY')

        if not key:
            # 首次运行，生成密钥
            key = Fernet.generate_key()
            print("\n" + "=" * 70)
            print("重要：请将以下加密密钥添加到.env文件中:")
            print(f"ENCRYPTION_KEY={key.decode()}")
            print("=" * 70 + "\n")
            # 暂时使用新生成的密钥
            self.cipher = Fernet(key)
        else:
            key = key.encode() if isinstance(key, str) else key
            self.cipher = Fernet(key)

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
