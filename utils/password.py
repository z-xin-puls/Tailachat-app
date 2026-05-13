# 密码加密工具模块
"""
使用bcrypt进行密码加密和验证
bcrypt是专门为密码哈希设计的算法，内置盐值管理
"""

import bcrypt

def hash_password(password):
    """
    生成密码哈希
    
    Args:
        password (str): 明文密码
        
    Returns:
        str: 加密后的密码哈希
    """
    # 生成盐值并加密密码
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password, hashed):
    """
    验证密码
    
    Args:
        password (str): 明文密码
        hashed (str): 存储的密码哈希
        
    Returns:
        bool: 密码是否匹配
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        # 如果哈希格式不正确，返回False
        return False

def is_hashed_password(password):
    """
    检查密码是否已经是哈希格式
    
    Args:
        password (str): 要检查的密码
        
    Returns:
        bool: 是否为哈希密码
    """
    # bcrypt哈希通常以$2b$开头，长度为60字符
    return password.startswith('$2b$') and len(password) == 60
