# 自定义异常类 - 统一错误处理
"""
这个文件定义了项目中使用的自定义异常类
用于统一错误处理和响应格式
"""

class AppError(Exception):
    """应用基础异常类"""
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class ValidationError(AppError):
    """输入验证错误"""
    def __init__(self, message):
        super().__init__(message, 400)

class AuthenticationError(AppError):
    """认证错误"""
    def __init__(self, message):
        super().__init__(message, 401)

class AuthorizationError(AppError):
    """权限错误"""
    def __init__(self, message):
        super().__init__(message, 403)

class NotFoundError(AppError):
    """资源不存在错误"""
    def __init__(self, message):
        super().__init__(message, 404)

class ConflictError(AppError):
    """业务冲突错误"""
    def __init__(self, message):
        super().__init__(message, 409)

class DatabaseError(AppError):
    """数据库操作错误"""
    def __init__(self, message):
        super().__init__(message, 500)
