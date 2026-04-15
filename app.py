# 小T语音应用 - 重构版本
from flask import Flask, render_template, request, redirect, session, send_from_directory
import mysql.connector
import sys
import subprocess
import os
import requests
import socket
import json
import threading
from datetime import datetime
import time

# 导入配置
from config import SECRET_KEY, DB_CONFIG, PROFILE_CACHE_TTL_SECONDS

# 导入数据模型
from models.database import get_db_connection, ensure_user_profile_columns, ensure_room_location_columns
from models.user import get_user_profiles, clear_user_profile_cache, resolve_avatar_url, format_user_label
from models.room import get_room_by_id, create_room

# 导入数据库初始化
from init_db import init_database

# 导入验证函数
from utils.validators import validate_room_name

# 导入路由蓝图
from routes.auth import auth_bp
from routes.main import main_bp
from routes.profile import profile_bp

# 创建Flask应用
app = Flask(__name__)
app.secret_key = SECRET_KEY

# 全局变量
voice_processes = {}
room_users = {}
chat_rooms = {}
chat_lock = threading.Lock()

# 注册蓝图
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(profile_bp)

# 初始化数据库表结构
init_database()

# 初始化数据库结构
@app.before_request
def _init_profile_schema():
    ensure_user_profile_columns()
    ensure_room_location_columns()

# 剩余的路由（房间相关、API等）
@app.route('/room/<id>')
def room(id):
    if "user" not in session:
        return redirect("/login")

    user = session['user']
    if id not in room_users:
        room_users[id] = set()
    room_users[id].add(user)

    voice_users = []
    speaking_user = None
    try:
        response = requests.get(f'http://127.0.0.1:5001/api/room-users/{id}', timeout=2)
        if response.status_code == 200:
            data = response.json()
            voice_users = data.get('users', [])
            speaking_user = data.get('speaking')
    except:
        pass

    web_users = room_users.get(id, set())
    all_users = web_users | set(voice_users)
    count = len(all_users)

    profiles = get_user_profiles(all_users)
    self_prof = profiles.get(user) or get_user_profiles([user]).get(user) or {}
    self_display = (self_prof.get("nickname") or user)

    member_items = ""
    for u in sorted(all_users):
        safe_u = u.replace("'", "").replace('"', "")
        label = format_user_label(u, profiles.get(u))
        info_link = f"<a class='user-info' href='/user/{safe_u}' onclick=\"event.stopPropagation();\">资料</a>"
        if u == speaking_user:
            member_items += f"<li class='user-item speaking' onclick=\"openVolumePanel('{safe_u}')\"><div class='user-main'><span class='badge badge-green'>说话</span>{label}</div><div class='user-meta'>🎤 {info_link}</div></li>"
        elif u in voice_users:
            member_items += f"<li class='user-item voice' onclick=\"openVolumePanel('{safe_u}')\"><div class='user-main'><span class='badge badge-teal'>语音</span>{label}</div><div class='user-meta'>✅ {info_link}</div></li>"
        else:
            member_items += f"<li class='user-item online' onclick=\"openVolumePanel('{safe_u}')\"><div class='user-main'><span class='badge badge-gray'>在线</span>{label}</div><div class='user-meta'>• {info_link}</div></li>"

    return render_template('rooms/room.html',
                         room_id=id,
                         current_user=self_display,
                         user_count=count,
                         member_items=member_items)

# API路由

# API路由
@app.route('/api/chat/history/<room_id>')
def chat_history(room_id):
    if "user" not in session:
        return {"success": False, "error": "未登录", "messages": []}
    after = request.args.get("after")
    try:
        after = int(after) if after is not None else 0
    except:
        after = 0
    room = chat_rooms.get(room_id)
    if room is None:
        room = {"next_id": 1, "messages": []}
        chat_rooms[room_id] = room
    with chat_lock:
        msgs = [m for m in room["messages"] if m["id"] > after]
    return {"success": True, "messages": msgs[-100:]}

@app.route('/api/chat/send/<room_id>', methods=['POST'])
def chat_send(room_id):
    if "user" not in session:
        return {"success": False, "error": "未登录"}
    text = None
    if request.is_json:
        text = request.json.get("text")
    if text is None:
        text = request.form.get("text")
    if text is None:
        return {"success": False, "error": "参数错误"}
    text = str(text).strip()
    if not text:
        return {"success": False, "error": "消息不能为空"}
    if len(text) > 500:
        return {"success": False, "error": "消息过长"}

    room = chat_rooms.get(room_id)
    if room is None:
        room = {"next_id": 1, "messages": []}
        chat_rooms[room_id] = room
    prof = get_user_profiles([session["user"]]).get(session["user"]) or {}
    chat_user = (prof.get("nickname") or session["user"])
    with chat_lock:
        msg_id = room["next_id"]
        room["next_id"] += 1
        room["messages"].append({
            "id": msg_id,
            "user": chat_user,
            "text": text,
            "time": datetime.now().strftime("%H:%M:%S")
        })
        if len(room["messages"]) > 500:
            room["messages"] = room["messages"][-500:]

    return {"success": True}

@app.route('/api/volume/mic', methods=['POST'])
def set_mic_volume():
    if "user" not in session:
        return {"success": False, "error": "未登录"}
    gain = None
    if request.is_json:
        gain = request.json.get("gain")
    if gain is None:
        gain = request.form.get("gain") or request.args.get("gain")
    try:
        gain = float(gain)
    except:
        return {"success": False, "error": "参数错误"}
    gain = max(0.0, min(2.0, gain))
    ok, err = send_voice_control(session["user"], {"type": "mic", "gain": gain})
    return {"success": ok, "error": err}

@app.route('/api/volume/playback', methods=['POST'])
def set_playback_volume():
    if "user" not in session:
        return {"success": False, "error": "未登录"}
    target = None
    gain = None
    if request.is_json:
        target = request.json.get("target")
        gain = request.json.get("gain")
    if target is None:
        target = request.form.get("target") or request.args.get("target")
    if gain is None:
        gain = request.form.get("gain") or request.args.get("gain")
    if not target:
        return {"success": False, "error": "参数错误"}
    try:
        gain = float(gain)
    except:
        return {"success": False, "error": "参数错误"}
    gain = max(0.0, min(2.0, gain))
    ok, err = send_voice_control(session["user"], {"type": "playback", "target": str(target), "gain": gain})
    return {"success": ok, "error": err}

# 语音控制相关函数
def allocate_local_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def get_voice_entry(username):
    entry = voice_processes.get(username)
    if entry is None:
        return None
    if isinstance(entry, dict):
        return entry
    return {"proc": entry, "control_port": None}

def terminate_voice_entry(entry):
    if not entry:
        return
    proc = entry.get("proc") if isinstance(entry, dict) else entry
    if proc is None:
        return
    try:
        proc.terminate()
    except:
        pass

def send_voice_control(username, payload):
    entry = get_voice_entry(username)
    if not entry or not entry.get("control_port"):
        return False, "语音客户端未运行"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect(("127.0.0.1", int(entry["control_port"])))
        msg = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        s.sendall(msg)
        s.close()
        return True, None
    except Exception as e:
        return False, str(e)

# 语音相关路由
@app.route('/start-voice/<room_id>')
def start_voice(room_id):
    if "user" not in session:
        return {"success": False, "error": "未登录"}

    username = session['user']
    client_path = os.path.join(os.path.dirname(__file__), 'scripts/client.py')

    try:
        existing = get_voice_entry(username)
        terminate_voice_entry(existing)

        control_port = allocate_local_port()

        if os.name == 'nt':
            proc = subprocess.Popen([sys.executable, client_path, username, room_id, str(control_port)], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            proc = subprocess.Popen([sys.executable, client_path, username, room_id, str(control_port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        voice_processes[username] = {"proc": proc, "control_port": control_port}
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route('/stop-voice')
def stop_voice():
    if "user" not in session:
        return {"success": False, "error": "未登录"}
    user = session['user']
    if user in voice_processes:
        try:
            terminate_voice_entry(get_voice_entry(user))
            del voice_processes[user]
            return {"success": True}
        except:
            return {"success": False, "error": "关闭失败"}
    return {"success": False, "error": "未运行"}

@app.route('/leave-room/<room_id>')
def leave_room(room_id):
    if "user" not in session: return redirect("/login")
    user = session["user"]
    if room_id in room_users:
        room_users[room_id].discard(user)
    try:
        stop_voice()
    except:
        pass
    return redirect("/")

@app.route('/room-data/<id>')
def room_data(id):
    voice_users = []
    speaking_user = None
    try:
        res = requests.get(f'http://127.0.0.1:5001/api/room-users/{id}', timeout=1)
        if res.status_code == 200:
            d = res.json()
            voice_users = d.get('users', [])
            speaking_user = d.get('speaking')
    except:
        pass

    web_users = room_users.get(id, set())
    all_users = web_users | set(voice_users)

    profiles = get_user_profiles(all_users)
    members = ''
    for u in sorted(all_users):
        safe_u = u.replace("'", "").replace('"', "")
        label = format_user_label(u, profiles.get(u))
        info_link = f"<a class='user-info' href='/user/{safe_u}' onclick=\"event.stopPropagation();\">资料</a>"
        if u == speaking_user:
            members += f"<li class='user-item speaking' onclick=\"openVolumePanel('{safe_u}')\"><div class='user-main'><span class='badge badge-green'>说话</span>{label}</div><div class='user-meta'>🎤 {info_link}</div></li>"
        elif u in voice_users:
            members += f"<li class='user-item voice' onclick=\"openVolumePanel('{safe_u}')\"><div class='user-main'><span class='badge badge-teal'>语音</span>{label}</div><div class='user-meta'>✅ {info_link}</div></li>"
        else:
            members += f"<li class='user-item online' onclick=\"openVolumePanel('{safe_u}')\"><div class='user-main'><span class='badge badge-gray'>在线</span>{label}</div><div class='user-meta'>• {info_link}</div></li>"

    return {"count": len(all_users), "members": members}

# 传统创建房间路由（保留兼容性）
@app.route('/create', methods=['GET','POST'])
def create():
    if "user" not in session: return redirect("/login")
    if request.method == 'POST':
        name = request.form['name']
        error = validate_room_name(name)
        if error: return f"<h3>{error}</h3>"
        
        room_id, error = create_room(name, session['user'])
        if error:
            return f"<h3>{error}</h3>"
        
        return redirect("/")
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>小T语音 - 创建房间</title>
        <style>
            *{margin:0;padding:0;box-sizing:border-box}
            body{background:#111827;color:#fff;font-family:Segoe UI,微软雅黑;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:28px}
            a{text-decoration:none;color:#2dd4bf}
            .wrap{width:100%;max-width:520px}
            .brand{color:#2dd4bf;font-size:24px;font-weight:900;letter-spacing:.5px}
            .sub{color:#9ca3af;margin-top:6px;font-size:13px}
            .card{margin-top:18px;background:#1f2937;border:1px solid #111827;border-radius:16px;padding:22px;box-shadow:0 0 24px #0006}
            .field{margin-top:12px}
            .label{font-size:12px;color:#cbd5e1;margin-bottom:6px}
            input{width:100%;padding:12px 14px;background:#111827;border:1px solid #374151;color:#fff;border-radius:10px;font-size:14px;outline:none}
            input:focus{border-color:#2dd4bf;box-shadow:0 0 0 3px #2dd4bf22}
            .row{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap}
            .btn{flex:1;min-width:160px;background:#2dd4bf;color:#111;font-weight:900;border:none;padding:12px 14px;border-radius:10px;cursor:pointer;text-align:center}
            .btn:hover{filter:brightness(1.03)}
            .btn-ghost{background:transparent;color:#e5e7eb;border:1px solid #374151}
        </style>
    </head>
    <body>
        <div class="wrap">
            <div class="brand">创建房间</div>
            <div class="sub">输入房间名称后创建，创建完成会返回首页列表</div>
            <div class="card">
                <form method="post">
                    <div class="field">
                        <div class="label">房间名称</div>
                        <input name="name" placeholder="输入房间名称" required>
                    </div>
                    <div class="row">
                        <button class="btn" type="submit">创建</button>
                        <a class="btn btn-ghost" href="/">返回</a>
                    </div>
                </form>
            </div>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    import logging
    # 配置日志级别，只输出警告及以上级别的信息
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.WARNING)
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
