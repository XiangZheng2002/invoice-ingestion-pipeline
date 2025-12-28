import sqlite3
from datetime import datetime
import os

def get_db_connection(db_path):
    """获取数据库连接"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path):
    """初始化数据库"""
    # 确保数据目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 创建emails表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id TEXT UNIQUE NOT NULL,
            subject TEXT,
            sender TEXT,
            received_date DATETIME,
            is_invoice BOOLEAN DEFAULT 0,
            processed BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建invoices表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id TEXT,
            invoice_code TEXT,
            invoice_number TEXT,
            invoice_type TEXT,
            invoice_date DATE,
            buyer_name TEXT,
            seller_name TEXT,
            total_amount DECIMAL(10,2),
            tax_amount DECIMAL(10,2),
            total_with_tax DECIMAL(10,2),
            file_path TEXT,
            ocr_confidence FLOAT,
            verified BOOLEAN DEFAULT 0,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (email_id) REFERENCES emails(email_id)
        )
    ''')

    # 创建config表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            encrypted BOOLEAN DEFAULT 0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建export_history表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS export_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            record_count INTEGER,
            export_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print(f"数据库初始化完成: {db_path}")

class Email:
    """邮件模型"""

    @staticmethod
    def create(db_path, email_data):
        """创建邮件记录"""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO emails
            (email_id, subject, sender, received_date, is_invoice, processed)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            email_data['email_id'],
            email_data['subject'],
            email_data['sender'],
            email_data['received_date'],
            email_data.get('is_invoice', False),
            email_data.get('processed', False)
        ))

        conn.commit()
        email_id = cursor.lastrowid
        conn.close()
        return email_id

    @staticmethod
    def get_all(db_path, limit=100, offset=0):
        """获取所有邮件"""
        conn = get_db_connection(db_path)
        emails = conn.execute(
            'SELECT * FROM emails ORDER BY received_date DESC LIMIT ? OFFSET ?',
            (limit, offset)
        ).fetchall()
        conn.close()
        return emails

    @staticmethod
    def get_by_id(db_path, email_id):
        """根据ID获取邮件"""
        conn = get_db_connection(db_path)
        email = conn.execute(
            'SELECT * FROM emails WHERE email_id = ?',
            (email_id,)
        ).fetchone()
        conn.close()
        return email

    @staticmethod
    def count(db_path, is_invoice=None):
        """统计邮件数量"""
        conn = get_db_connection(db_path)
        if is_invoice is not None:
            count = conn.execute(
                'SELECT COUNT(*) FROM emails WHERE is_invoice = ?',
                (is_invoice,)
            ).fetchone()[0]
        else:
            count = conn.execute('SELECT COUNT(*) FROM emails').fetchone()[0]
        conn.close()
        return count

class Invoice:
    """发票模型"""

    @staticmethod
    def create(db_path, invoice_data):
        """创建发票记录"""
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO invoices
            (email_id, invoice_code, invoice_number, invoice_type, invoice_date,
             buyer_name, seller_name, total_amount, tax_amount, total_with_tax,
             file_path, ocr_confidence, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            invoice_data.get('email_id'),
            invoice_data.get('invoice_code'),
            invoice_data.get('invoice_number'),
            invoice_data.get('invoice_type'),
            invoice_data.get('invoice_date'),
            invoice_data.get('buyer_name'),
            invoice_data.get('seller_name'),
            invoice_data.get('total_amount'),
            invoice_data.get('tax_amount'),
            invoice_data.get('total_with_tax'),
            invoice_data.get('file_path'),
            invoice_data.get('ocr_confidence'),
            invoice_data.get('notes')
        ))

        conn.commit()
        invoice_id = cursor.lastrowid
        conn.close()
        return invoice_id

    @staticmethod
    def get_all(db_path, limit=100, offset=0):
        """获取所有发票"""
        conn = get_db_connection(db_path)
        invoices = conn.execute(
            'SELECT * FROM invoices ORDER BY created_at DESC LIMIT ? OFFSET ?',
            (limit, offset)
        ).fetchall()
        conn.close()
        return invoices

    @staticmethod
    def get_by_id(db_path, invoice_id):
        """根据ID获取发票"""
        conn = get_db_connection(db_path)
        invoice = conn.execute(
            'SELECT * FROM invoices WHERE id = ?',
            (invoice_id,)
        ).fetchone()
        conn.close()
        return invoice

    @staticmethod
    def count(db_path):
        """统计发票数量"""
        conn = get_db_connection(db_path)
        count = conn.execute('SELECT COUNT(*) FROM invoices').fetchone()[0]
        conn.close()
        return count

    @staticmethod
    def get_total_amount(db_path):
        """获取发票总金额"""
        conn = get_db_connection(db_path)
        result = conn.execute(
            'SELECT SUM(total_with_tax) FROM invoices'
        ).fetchone()[0]
        conn.close()
        return result or 0.0

class Config:
    """配置模型"""

    @staticmethod
    def get(db_path, key, default=None):
        """获取配置值"""
        conn = get_db_connection(db_path)
        result = conn.execute(
            'SELECT value, encrypted FROM config WHERE key = ?',
            (key,)
        ).fetchone()
        conn.close()

        if result:
            value, encrypted = result
            if encrypted:
                # 需要解密
                from app.utils.crypto import CryptoUtil
                crypto = CryptoUtil()
                return crypto.decrypt(value)
            return value
        return default

    @staticmethod
    def set(db_path, key, value, encrypted=False):
        """设置配置值"""
        if encrypted:
            # 加密值
            from app.utils.crypto import CryptoUtil
            crypto = CryptoUtil()
            value = crypto.encrypt(value)

        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO config (key, value, encrypted, updated_at)
            VALUES (?, ?, ?, ?)
        ''', (key, value, encrypted, datetime.now()))

        conn.commit()
        conn.close()
