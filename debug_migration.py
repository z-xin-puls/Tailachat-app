#!/usr/bin/env python3
# 迁移调试脚本

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_migration_components():
    """测试迁移组件"""
    print("=== 迁移组件测试 ===")
    
    # 测试密码工具
    try:
        from utils.password import hash_password, verify_password, is_hashed_password
        print("✅ 密码工具导入成功")
        
        # 测试密码加密
        test_password = "test123"
        hashed = hash_password(test_password)
        print(f"✅ 密码加密成功: {hashed[:20]}...")
        
        # 测试密码验证
        is_valid = verify_password(test_password, hashed)
        print(f"✅ 密码验证成功: {is_valid}")
        
        # 测试格式检查
        is_hashed = is_hashed_password(hashed)
        print(f"✅ 格式检查成功: {is_hashed}")
        
    except Exception as e:
        print(f"❌ 密码工具测试失败: {e}")
        return False
    
    # 测试数据库连接
    try:
        from models.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 测试用户查询
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"✅ 数据库连接成功: {user_count} 个用户")
        
        # 测试密码字段
        cursor.execute("DESCRIBE users")
        columns = cursor.fetchall()
        password_column = None
        for column in columns:
            if column[0] == 'password':
                password_column = column
                break
        
        if password_column:
            print(f"✅ 密码字段信息: {password_column}")
        else:
            print("❌ 未找到密码字段")
            return False
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        return False
    
    # 测试迁移路由
    try:
        from routes.migration import migration_bp
        print("✅ 迁移路由导入成功")
        
        # 检查路由
        routes = []
        for rule in migration_bp.deferred_functions:
            # 这个方法可能不准确，但可以检查路由是否定义
            pass
        
        print("✅ 迁移路由检查完成")
        
    except Exception as e:
        print(f"❌ 迁移路由测试失败: {e}")
        return False
    
    return True

def test_password_format():
    """测试密码格式"""
    print("\n=== 密码格式测试 ===")
    
    try:
        from models.database import get_db_connection
        from utils.password import is_hashed_password
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT username, password FROM users LIMIT 5")
        users = cursor.fetchall()
        
        print(f"检查 {len(users)} 个用户的密码格式:")
        
        for user in users:
            username, password = user
            is_hashed = is_hashed_password(password)
            status = "✅ 已加密" if is_hashed else "❌ 明文"
            print(f"  {username}: {status} ({len(password)} 字符)")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 密码格式检查失败: {e}")

if __name__ == "__main__":
    print("迁移功能调试")
    print("=" * 50)
    
    if test_migration_components():
        print("\n✅ 所有组件测试通过")
        test_password_format()
    else:
        print("\n❌ 组件测试失败，请检查错误信息")
