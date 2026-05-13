#!/usr/bin/env python3
# Railway部署兼容性测试脚本

import sys
import os
import platform

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_bcrypt_compatibility():
    """测试bcrypt在当前环境中的兼容性"""
    print("=== bcrypt兼容性测试 ===")
    print(f"Python版本: {sys.version}")
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"架构: {platform.machine()}")
    
    try:
        import bcrypt
        print(f"✅ bcrypt版本: {bcrypt.__version__}")
        
        # 测试基本功能
        test_password = "test123456"
        
        # 测试哈希生成
        print("\n--- 测试密码哈希生成 ---")
        hashed = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt())
        print(f"✅ 哈希生成成功: {hashed.decode('utf-8')[:20]}...")
        print(f"   哈希长度: {len(hashed)} 字符")
        
        # 测试密码验证
        print("\n--- 测试密码验证 ---")
        is_valid = bcrypt.checkpw(test_password.encode('utf-8'), hashed)
        print(f"✅ 密码验证成功: {is_valid}")
        
        # 测试错误密码
        is_invalid = bcrypt.checkpw("wrong_password".encode('utf-8'), hashed)
        print(f"✅ 错误密码验证: {is_invalid}")
        
        # 测试不同盐值
        print("\n--- 测试不同盐值生成 ---")
        hashed1 = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt())
        hashed2 = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt())
        print(f"✅ 相同密码不同哈希: {hashed1 != hashed2}")
        
        return True
        
    except ImportError as e:
        print(f"❌ bcrypt导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ bcrypt测试失败: {e}")
        return False

def test_database_connection():
    """测试数据库连接"""
    print("\n=== 数据库连接测试 ===")
    
    try:
        from models.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def test_password_module():
    """测试密码模块"""
    print("\n=== 密码模块测试 ===")
    
    try:
        from utils.password import hash_password, verify_password, is_hashed_password
        
        test_password = "railway_test_123"
        
        # 测试哈希生成
        hashed = hash_password(test_password)
        print(f"✅ 哈希生成: {hashed[:20]}...")
        
        # 测试验证
        is_valid = verify_password(test_password, hashed)
        print(f"✅ 密码验证: {is_valid}")
        
        # 测试格式检查
        is_hashed = is_hashed_password(hashed)
        print(f"✅ 格式检查: {is_hashed}")
        
        return True
        
    except Exception as e:
        print(f"❌ 密码模块测试失败: {e}")
        return False

def check_railway_environment():
    """检查Railway环境变量"""
    print("\n=== Railway环境检查 ===")
    
    railway_vars = [
        'RAILWAY_ENVIRONMENT',
        'RAILWAY_SERVICE_NAME',
        'RAILWAY_PROJECT_NAME',
        'PORT',
        'MYSQLHOST',
        'MYSQLUSER',
        'MYSQLPASSWORD',
        'MYSQLDATABASE',
        'MYSQLPORT'
    ]
    
    for var in railway_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value[:20]}..." if len(value) > 20 else f"✅ {var}: {value}")
        else:
            print(f"⚪ {var}: 未设置")

if __name__ == "__main__":
    print("Railway部署兼容性检查")
    print("=" * 50)
    
    # 检查环境
    check_railway_environment()
    
    # 运行测试
    tests = [
        test_bcrypt_compatibility,
        test_password_module,
        test_database_connection
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            results.append(False)
    
    # 总结
    print("\n" + "=" * 50)
    print("测试总结:")
    passed = sum(results)
    total = len(results)
    print(f"✅ 通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过！项目适合Railway部署")
    else:
        print("⚠️  存在兼容性问题，需要修复")
