# 数据库基础操作
import os
import mysql.connector
import psycopg2
from config import DB_CONFIG, DATABASE_URL

def get_db_connection():
    """获取数据库连接 - 支持 MySQL 和 PostgreSQL"""
    # 如果设置了 DATABASE_URL（Railway + Aiven），使用 PostgreSQL
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    
    # 否则使用本地 MySQL
    return mysql.connector.connect(**DB_CONFIG)

def ensure_user_profile_columns():
    """确保用户表有头像和昵称字段"""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # 根据数据库类型使用不同的语法
        if DATABASE_URL:
            # PostgreSQL 语法
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'nickname'
            """)
            has_nickname = cursor.fetchone() is not None
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'avatar'
            """)
            has_avatar = cursor.fetchone() is not None
        else:
            # MySQL 语法
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
        
        # 根据数据库类型使用不同的语法
        if DATABASE_URL:
            # PostgreSQL 语法
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'rooms' AND column_name = 'x'
            """)
            has_x = cursor.fetchone() is not None
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'rooms' AND column_name = 'y'
            """)
            has_y = cursor.fetchone() is not None
        else:
            # MySQL 语法
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
