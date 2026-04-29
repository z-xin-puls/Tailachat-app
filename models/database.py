# 数据库基础操作
import mysql.connector
from config import DB_CONFIG

def get_db_connection():
    """获取数据库连接"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SET time_zone = '+08:00'")
    conn.commit()
    cursor.close()
    return conn

def ensure_user_profile_columns():
    """确保用户表有头像和昵称字段"""
    db = None
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SHOW COLUMNS FROM users LIKE 'nickname'")
        has_nickname = cursor.fetchone() is not None
        cursor.execute("SHOW COLUMNS FROM users LIKE 'avatar'")
        has_avatar = cursor.fetchone() is not None
        if not has_nickname:
            cursor.execute("ALTER TABLE users ADD COLUMN nickname VARCHAR(30) NULL DEFAULT NULL")
        if not has_avatar:
            cursor.execute("ALTER TABLE users ADD COLUMN avatar VARCHAR(255) NULL DEFAULT NULL")
        db.commit()
        cursor.close()
        db.close()
    except Exception as e:
        print(f"确保用户表字段失败: {e}")
        if db:
            try:
                db.close()
            except:
                pass
