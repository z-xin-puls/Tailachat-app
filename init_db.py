# 数据库初始化脚本 - 自动创建表结构
from models.database import get_db_connection

def init_database():
    """初始化数据库表结构"""
    try:
        db = get_db_connection()
        cursor = db.cursor()

        # 检查表是否已存在
        cursor.execute("SHOW TABLES")
        existing_tables = [table[0] for table in cursor.fetchall()]

        # 创建 users 表
        if 'users' not in existing_tables:
            cursor.execute("""
                CREATE TABLE users (
                    username VARCHAR(50) PRIMARY KEY,
                    password VARCHAR(255) NOT NULL,
                    nickname VARCHAR(30) NULL DEFAULT NULL,
                    avatar VARCHAR(255) NULL DEFAULT NULL
                )
            """)
            print("✅ 创建 users 表")

        # 创建 rooms 表
        if 'rooms' not in existing_tables:
            cursor.execute("""
                CREATE TABLE rooms (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    owner VARCHAR(50) NOT NULL,
                    x FLOAT NULL DEFAULT NULL,
                    y FLOAT NULL DEFAULT NULL,
                    fortress_id INT NULL DEFAULT NULL,
                    FOREIGN KEY (owner) REFERENCES users(username) ON DELETE CASCADE
                )
            """)
            print("✅ 创建 rooms 表")

        # 创建 fortresses 表
        if 'fortresses' not in existing_tables:
            cursor.execute("""
                CREATE TABLE fortresses (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    x FLOAT NOT NULL,
                    y FLOAT NOT NULL,
                    radius FLOAT NULL DEFAULT NULL,
                    color VARCHAR(50) NULL DEFAULT NULL,
                    description TEXT NULL DEFAULT NULL,
                    image VARCHAR(255) NULL DEFAULT NULL
                )
            """)
            print("✅ 创建 fortresses 表")

        # 创建 user_log 表
        if 'user_log' not in existing_tables:
            cursor.execute("""
                CREATE TABLE user_log (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ip VARCHAR(50) NOT NULL,
                    connect_time DATETIME NOT NULL
                )
            """)
            print("✅ 创建 user_log 表")

        db.commit()
        db.close()
        return True
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        try:
            db.close()
        except:
            pass
        return False

if __name__ == "__main__":
    init_database()
