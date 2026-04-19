# 权限检查装饰器
from functools import wraps
from flask import session, redirect, flash

def admin_required(f):
    """管理员权限检查装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        
        # 检查用户是否为管理员
        from models.user import is_admin
        if not is_admin(session['user']):
            flash('需要管理员权限才能访问此页面')
            return redirect('/')
        
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    """登录检查装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function
