# 登录注册路由
from flask import Blueprint, request, redirect, render_template_string, session
from models.database import get_db_connection
from models.user import get_user_profiles
from utils.validators import validate_username, validate_password
from utils.helpers import html_escape

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = request.form['user']
        pwd = request.form['pwd']
        error = validate_username(user)
        if error: return f"<h3>{error}</h3>"
        error = validate_password(pwd)
        if error: return f"<h3>{error}</h3>"

        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (user,pwd))
        res = cursor.fetchone()
        db.close()
        if res:
            session['user'] = user
            return redirect("/")
        else:
            return "<h3>账号或密码错误</h3>"
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>泰拉通讯 - 登录</title>
        <style>
            *{margin:0;padding:0;box-sizing:border-box}
            body{background:#111827;color:#fff;font-family:Segoe UI,微软雅黑;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:28px}
            a{text-decoration:none;color:#2dd4bf}
            .wrap{width:100%;max-width:420px}
            .brand{color:#2dd4bf;font-size:26px;font-weight:900;letter-spacing:.5px}
            .sub{color:#9ca3af;margin-top:6px;font-size:13px}
            .card{margin-top:18px;background:#1f2937;border:1px solid #111827;border-radius:16px;padding:22px;box-shadow:0 0 24px #0006}
            .field{margin-top:12px}
            .label{font-size:12px;color:#cbd5e1;margin-bottom:6px}
            input{width:100%;padding:12px 14px;background:#111827;border:1px solid #374151;color:#fff;border-radius:10px;font-size:14px;outline:none}
            input:focus{border-color:#2dd4bf;box-shadow:0 0 0 3px #2dd4bf22}
            .row{display:flex;gap:10px;align-items:center;justify-content:space-between;margin-top:16px;flex-wrap:wrap}
            .btn{width:100%;background:#2dd4bf;color:#111;font-weight:900;border:none;padding:12px 14px;border-radius:10px;cursor:pointer}
            .btn:hover{filter:brightness(1.03)}
            .foot{margin-top:14px;text-align:center;color:#9ca3af;font-size:13px}
        </style>
    </head>
    <body>
        <div class="wrap">
            <div class="brand">🎤 泰拉通讯</div>
            <div class="sub">登录后进入房间，点击成员可独立调音量</div>
            <div class="card">
                <form method="post">
                    <div class="field">
                        <div class="label">账号</div>
                        <input name="user" placeholder="请输入账号" required>
                    </div>
                    <div class="field">
                        <div class="label">密码</div>
                        <input name="pwd" type="password" placeholder="请输入密码" required>
                    </div>
                    <div class="row">
                        <button class="btn" type="submit">登录</button>
                    </div>
                </form>
                <div class="foot">
                    没有账号？<a href="/reg">立即注册</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@auth_bp.route('/reg', methods=['GET','POST'])
def reg():
    if request.method == 'POST':
        user = request.form['user']
        pwd = request.form['pwd']
        error = validate_username(user)
        if error: return f"<h3>{error}</h3>"
        error = validate_password(pwd)
        if error: return f"<h3>{error}</h3>"

        try:
            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute("INSERT INTO users (username,password) VALUES (%s,%s)", (user,pwd))
            db.commit()
            db.close()
            return redirect("/login")
        except Exception as e:
            if "Duplicate" in str(e):
                return "<h3>用户名已存在！</h3>"
            else:
                return f"<h3>注册失败：{str(e)}</h3>"
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>泰拉通讯 - 注册</title>
        <style>
            *{margin:0;padding:0;box-sizing:border-box}
            body{background:#111827;color:#fff;font-family:Segoe UI,微软雅黑;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:28px}
            a{text-decoration:none;color:#2dd4bf}
            .wrap{width:100%;max-width:420px}
            .brand{color:#2dd4bf;font-size:26px;font-weight:900;letter-spacing:.5px}
            .sub{color:#9ca3af;margin-top:6px;font-size:13px}
            .card{margin-top:18px;background:#1f2937;border:1px solid #111827;border-radius:16px;padding:22px;box-shadow:0 0 24px #0006}
            .field{margin-top:12px}
            .label{font-size:12px;color:#cbd5e1;margin-bottom:6px}
            input{width:100%;padding:12px 14px;background:#111827;border:1px solid #374151;color:#fff;border-radius:10px;font-size:14px;outline:none}
            input:focus{border-color:#2dd4bf;box-shadow:0 0 0 3px #2dd4bf22}
            .btn{width:100%;margin-top:16px;background:#2dd4bf;color:#111;font-weight:900;border:none;padding:12px 14px;border-radius:10px;cursor:pointer}
            .btn:hover{filter:brightness(1.03)}
            .foot{margin-top:14px;text-align:center;color:#9ca3af;font-size:13px}
        </style>
    </head>
    <body>
        <div class="wrap">
            <div class="brand">🎤 泰拉通讯</div>
            <div class="sub">创建账号后即可进入房间开始交流</div>
            <div class="card">
                <form method="post">
                    <div class="field">
                        <div class="label">账号</div>
                        <input name="user" placeholder="设置账号" required>
                    </div>
                    <div class="field">
                        <div class="label">密码</div>
                        <input name="pwd" type="password" placeholder="设置密码" required>
                    </div>
                    <button class="btn" type="submit">注册</button>
                </form>
                <div class="foot">
                    已有账号？<a href="/login">返回登录</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@auth_bp.route('/logout')
def logout():
    user = session.get("user")
    session.clear()
    return redirect("/login")
