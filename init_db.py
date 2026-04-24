# 数据库初始化脚本 - 自动创建表结构
from models.database import get_db_connection

def init_database():
    """初始化数据库表结构"""
    try:
        print("正在连接数据库...")
        db = get_db_connection()
        cursor = db.cursor()

        # 检查表是否已存在
        cursor.execute("SHOW TABLES")
        existing_tables = [table[0] for table in cursor.fetchall()]
        print(f"现有表: {existing_tables}")

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
                    portrait_index INT NULL DEFAULT 0,
                    position_x FLOAT NULL DEFAULT 0,
                    position_y FLOAT NULL DEFAULT -600,
                    portrait_scale FLOAT NULL DEFAULT 1.0,
                    opacity FLOAT NULL DEFAULT 90,
                    FOREIGN KEY (owner) REFERENCES users(username) ON DELETE CASCADE
                )
            """)
            print("✅ 创建 rooms 表")
        else:
            # 检查并添加立绘配置字段
            cursor.execute("SHOW COLUMNS FROM rooms LIKE 'portrait_index'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE rooms ADD COLUMN portrait_index INT NULL DEFAULT 0")
            cursor.execute("SHOW COLUMNS FROM rooms LIKE 'position_x'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE rooms ADD COLUMN position_x FLOAT NULL DEFAULT 0")
            cursor.execute("SHOW COLUMNS FROM rooms LIKE 'position_y'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE rooms ADD COLUMN position_y FLOAT NULL DEFAULT -600")
            cursor.execute("SHOW COLUMNS FROM rooms LIKE 'portrait_scale'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE rooms ADD COLUMN portrait_scale FLOAT NULL DEFAULT 1.0")
            cursor.execute("SHOW COLUMNS FROM rooms LIKE 'opacity'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE rooms ADD COLUMN opacity FLOAT NULL DEFAULT 90")
            print("✅ 更新 rooms 表结构")

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

        # 创建 user_activity 表 - 用户活动统计
        if 'user_activity' not in existing_tables:
            cursor.execute("""
                CREATE TABLE user_activity (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL,
                    action VARCHAR(20) NOT NULL,
                    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    ip VARCHAR(50) NULL DEFAULT NULL,
                    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
                )
            """)
            print("✅ 创建 user_activity 表")

        # 创建 room_activity 表 - 房间活动统计
        if 'room_activity' not in existing_tables:
            cursor.execute("""
                CREATE TABLE room_activity (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    room_id INT NOT NULL,
                    room_name VARCHAR(100) NOT NULL,
                    action VARCHAR(20) NOT NULL,
                    owner VARCHAR(50) NOT NULL,
                    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
                    FOREIGN KEY (owner) REFERENCES users(username) ON DELETE CASCADE
                )
            """)
            print("✅ 创建 room_activity 表")

        db.commit()
        db.close()
        print("✅ 数据库初始化完成")
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
