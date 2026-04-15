# 数据库初始化脚本 - 自动创建表结构
from models.database import get_db_connection

def init_database():
    """初始化数据库表结构"""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # 创建 users 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(50) PRIMARY KEY,
                password VARCHAR(255) NOT NULL,
                nickname VARCHAR(30) NULL DEFAULT NULL,
                avatar VARCHAR(255) NULL DEFAULT NULL
            )
        """)
        
        # 创建 rooms 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                owner VARCHAR(50) NOT NULL,
                x FLOAT NULL DEFAULT NULL,
                y FLOAT NULL DEFAULT NULL,
                fortress_id INT NULL DEFAULT NULL,
                FOREIGN KEY (owner) REFERENCES users(username) ON DELETE CASCADE
            )
        """)
        
        # 创建 fortresses 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fortresses (
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
        
        # 创建 user_log 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ip VARCHAR(50) NOT NULL,
                connect_time DATETIME NOT NULL
            )
        """)
        
        db.commit()
        db.close()
        print("✅ 数据库表结构创建成功！")
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
