# 自动密码迁移工具
"""
在应用启动时自动执行密码迁移
无需手动干预，自动检测并迁移明文密码
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.password import hash_password, verify_password, is_hashed_password
from models.database import get_db_connection

def check_migration_needed():
    """检查是否需要密码迁移"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 统计密码状态
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as encrypted FROM users WHERE password LIKE '$2b$%'")
        encrypted_users = cursor.fetchone()[0]
        
        conn.close()
        
        plain_users = total_users - encrypted_users
        return plain_users > 0, plain_users, total_users, encrypted_users
        
    except Exception as e:
        print(f"检查迁移状态失败: {e}")
        return False, 0, 0, 0

def prepare_database():
    """准备数据库 - 修改密码字段长度"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查当前密码字段长度
        cursor.execute("""
            SELECT CHARACTER_MAXIMUM_LENGTH 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'password'
        """)
        result = cursor.fetchone()
        
        if result and result[0] < 60:
            # 修改密码字段长度
            cursor.execute("ALTER TABLE users MODIFY COLUMN password VARCHAR(100)")
            conn.commit()
            print(f"✅ 密码字段长度已从 {result[0]} 修改为 100")
        else:
            print("✅ 密码字段长度已足够")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 准备数据库失败: {e}")
        return False

def execute_auto_migration():
    """执行自动密码迁移"""
    try:
        # 准备数据库
        if not prepare_database():
            return False
        
        # 检查是否需要迁移
        migration_needed, plain_users, total_users, encrypted_users = check_migration_needed()
        
        if not migration_needed:
            print(f"✅ 无需迁移: {encrypted_users}/{total_users} 个用户已加密")
            return True
        
        print(f"🚀 开始自动迁移: {plain_users} 个用户需要加密")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取所有明文密码用户
        cursor.execute("""
            SELECT id, username, password 
            FROM users 
            WHERE password NOT LIKE '$2b$%'
            ORDER BY id
        """)
        users = cursor.fetchall()
        
        migrated_count = 0
        failed_count = 0
        
        for user in users:
            user_id, username, password = user
            
            try:
                # 加密密码
                hashed_password = hash_password(password)
                cursor.execute("UPDATE users SET password = %s WHERE id = %s", 
                             (hashed_password, user_id))
                migrated_count += 1
                print(f"✅ 已迁移用户: {username}")
                
            except Exception as e:
                failed_count += 1
                print(f"❌ 迁移用户 {username} 失败: {e}")
        
        # 提交更改
        conn.commit()
        conn.close()
        
        print(f"🎉 自动迁移完成: 成功 {migrated_count} 个，失败 {failed_count} 个")
        return migrated_count > 0
        
    except Exception as e:
        print(f"❌ 自动迁移失败: {e}")
        return False

def run_auto_migration():
    """运行自动迁移（应用启动时调用）"""
    print("🔐 检查密码迁移状态...")
    
    try:
        # 检查是否需要迁移
        migration_needed, plain_users, total_users, encrypted_users = check_migration_needed()
        
        if migration_needed:
            print(f"⚠️  发现 {plain_users} 个用户使用明文密码，开始自动迁移...")
            success = execute_auto_migration()
            
            if success:
                print("✅ 自动迁移成功完成")
            else:
                print("❌ 自动迁移失败，请检查日志")
        else:
            print(f"✅ 密码已加密: {encrypted_users}/{total_users} 个用户")
            
    except Exception as e:
        print(f"❌ 自动迁移过程出错: {e}")

if __name__ == "__main__":
    # 直接运行时执行自动迁移
    run_auto_migration()
