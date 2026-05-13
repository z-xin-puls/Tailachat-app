#!/usr/bin/env python3
# 自动迁移测试脚本

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_auto_migration():
    """测试自动迁移功能"""
    print("=== 自动迁移测试 ===")
    
    try:
        from models.database import get_db_connection
        from utils.password import hash_password, verify_password, is_hashed_password
        from utils.auto_migration import run_auto_migration
        
        # 1. 创建测试用户（明文密码）
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 删除测试用户（如果存在）
        cursor.execute("DELETE FROM users WHERE username LIKE 'test_%'")
        
        # 创建测试用户
        test_users = [
            ('test_user1', 'password123'),
            ('test_user2', 'password456'),
            ('test_user3', 'password789')
        ]
        
        for username, password in test_users:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", 
                         (username, password))
        
        conn.commit()
        conn.close()
        
        print(f"✅ 创建了 {len(test_users)} 个测试用户（明文密码）")
        
        # 2. 检查迁移前状态
        from utils.auto_migration import check_migration_needed
        migration_needed, plain_users, total_users, encrypted_users = check_migration_needed()
        print(f"📊 迁移前状态: {plain_users} 个明文密码，{encrypted_users} 个已加密")
        
        # 3. 执行自动迁移
        print("🚀 开始自动迁移...")
        run_auto_migration()
        
        # 4. 验证迁移结果
        migration_needed_after, plain_users_after, total_users_after, encrypted_users_after = check_migration_needed()
        print(f"📊 迁移后状态: {plain_users_after} 个明文密码，{encrypted_users_after} 个已加密")
        
        # 5. 测试密码验证
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT username, password FROM users WHERE username LIKE 'test_%'")
        users = cursor.fetchall()
        
        print("🔐 验证密码加密:")
        for username, stored_password in users:
            is_hashed = is_hashed_password(stored_password)
            status = "✅ 已加密" if is_hashed else "❌ 明文"
            print(f"  {username}: {status}")
            
            # 测试密码验证
            if is_hashed:
                original_password = username.replace('test_user', 'password')
                is_valid = verify_password(original_password, stored_password)
                verification_status = "✅ 验证通过" if is_valid else "❌ 验证失败"
                print(f"    密码验证: {verification_status}")
        
        # 6. 清理测试用户
        cursor.execute("DELETE FROM users WHERE username LIKE 'test_%'")
        conn.commit()
        conn.close()
        
        print("🧹 清理测试用户完成")
        
        # 7. 总结
        if plain_users_after == 0 and encrypted_users_after > encrypted_users:
            print("🎉 自动迁移测试成功！")
            return True
        else:
            print("❌ 自动迁移测试失败！")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    print("自动迁移功能测试")
    print("=" * 50)
    
    if test_auto_migration():
        print("\n✅ 所有测试通过，自动迁移功能正常工作")
    else:
        print("\n❌ 测试失败，请检查错误信息")
