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
        db.close()
    except:
        try:
            db.close()
        except:
            pass

def ensure_room_location_columns():
    """确保房间表有位置字段"""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SHOW COLUMNS FROM rooms LIKE 'x'")
        has_x = cursor.fetchone() is not None
        cursor.execute("SHOW COLUMNS FROM rooms LIKE 'y'")
        has_y = cursor.fetchone() is not None
        if not has_x:
            cursor.execute("ALTER TABLE rooms ADD COLUMN x FLOAT NULL DEFAULT NULL")
        if not has_y:
            cursor.execute("ALTER TABLE rooms ADD COLUMN y FLOAT NULL DEFAULT NULL")
        db.commit()
        db.close()
    except:
        try:
            db.close()
        except:
            pass
