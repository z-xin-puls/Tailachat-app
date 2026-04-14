# 表单验证函数
from config import (
    MAX_USERNAME_LENGTH, MIN_USERNAME_LENGTH,
    MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH,
    MAX_ROOM_NAME_LENGTH, MIN_ROOM_NAME_LENGTH
)

def validate_username(username):
    """验证用户名"""
    if not username:
        return "用户名不能为空"
    if len(username) < MIN_USERNAME_LENGTH:
        return f"用户名至少需要 {MIN_USERNAME_LENGTH} 个字符"
    if len(username) > MAX_USERNAME_LENGTH:
        return f"用户名不能超过 {MAX_USERNAME_LENGTH} 个字符"
    for char in username:
        if not (char.isalnum() or char == '_' or '一' <= char <= '鿿'):
            return "用户名只能包含字母、数字、中文和下划线"
    return None

def validate_password(password):
    """验证密码"""
    if not password:
        return "密码不能为空"
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"密码至少需要 {MIN_PASSWORD_LENGTH} 个字符"
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"密码不能超过 {MAX_PASSWORD_LENGTH} 个字符"
    return None

def validate_room_name(name):
    """验证房间名称"""
    if not name:
        return "房间名称不能为空"
    if len(name) < MIN_ROOM_NAME_LENGTH:
        return f"房间名称至少需要 {MIN_ROOM_NAME_LENGTH} 个字符"
    if len(name) > MAX_ROOM_NAME_LENGTH:
        return f"房间名称不能超过 {MAX_ROOM_NAME_LENGTH} 个字符"
    for char in name:
        if char in '<>"\'&':
            return "房间名称不能包含特殊字符"
    return None
