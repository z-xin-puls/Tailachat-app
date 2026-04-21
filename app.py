# 小T语音应用 - 重构版本
from gevent import monkey
monkey.patch_all()

from flask import Flask, render_template, request, redirect, session, send_from_directory, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import mysql.connector
import os
import requests
import json
import threading
from datetime import datetime
import logging

# 减少日志输出
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('engineio').setLevel(logging.WARNING)
logging.getLogger('socketio').setLevel(logging.WARNING)

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

# 导入TRTC助手
from utils.trtc_helper import gen_user_sig

# 导入路由蓝图
from routes.auth import auth_bp
from routes.main import main_bp
from routes.profile import profile_bp
from routes.admin import admin_bp

# 创建Flask应用
app = Flask(__name__)
app.secret_key = SECRET_KEY

# 初始化SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# 全局变量
chat_rooms = {}
chat_lock = threading.Lock()

# 注册蓝图
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(admin_bp)

# 初始化数据库结构
_db_initialized = False

@app.before_request
def _init_database():
    global _db_initialized
    if not _db_initialized:
        init_database()
        _db_initialized = True

@app.before_request
def _init_profile_schema():
    ensure_user_profile_columns()
    ensure_room_location_columns()

# 剩余的路由（房间相关、API等）
@app.route('/api/trtc/usersig')
def get_trtc_usersig():
    """生成TRTC UserSig"""
    # 接收前端传过来的英文ID
    user_id = request.args.get("userId", "guest")

    # 生成签名
    sig = gen_user_sig(user_id)
    return jsonify({
        "userSig": sig,
        "sdkAppId": 1600138234
    })

@app.route('/api/admin/realtime-stats')
def get_realtime_stats():
    """获取实时统计数据"""
    # 计算在线用户数
    online_users = 0
    active_rooms = 0

    # 统计语音房间用户
    for room_id, users in socket_room_users.items():
        online_users += len(users)
        active_rooms += 1

    # 统计房间页面用户（去重）
    page_users = set()
    for room_id, users in room_users.items():
        page_users.update(users)

    return jsonify({
        "online_users": online_users,
        "active_rooms": active_rooms,
        "page_users": len(page_users)
    })

@app.route('/room/<id>')
def room(id):
    if "user" not in session:
        return redirect("/login")

    user = session['user']

    # 添加用户到房间
    if id not in room_users:
        room_users[id] = set()
    room_users[id].add(user)

    # 获取语音用户列表
    voice_users = []
    if id in socket_room_users:
        voice_users = list(socket_room_users[id].values())

    # 合并房间页面用户和语音用户
    web_users = room_users.get(id, set())
    all_users = web_users | set(voice_users)
    count = len(all_users)

    profiles = get_user_profiles(all_users)
    self_prof = profiles.get(user) or {}
    self_display = (self_prof.get("nickname") or user)

    # 生成member_items HTML
    member_items = ""
    for u in sorted(all_users):
        safe_u = u.replace("'", "").replace('"', "")
        label = format_user_label(u, profiles.get(u))
        info_link = f"<a class='user-info' href='/user/{safe_u}' onclick=\"event.stopPropagation();\">资料</a>"
        if u in voice_users:
            member_items += f"<li class='user-item voice' onclick=\"openVolumePanel('{safe_u}')\"><div class='user-main'><span class='badge badge-teal'>语音</span>{label}</div><div class='user-meta'>✅ {info_link}</div></li>"
        else:
            member_items += f"<li class='user-item online' onclick=\"openVolumePanel('{safe_u}')\"><div class='user-main'><span class='badge badge-gray'>在线</span>{label}</div><div class='user-meta'>• {info_link}</div></li>"

    return render_template('rooms/room.html',
                         room_id=id,
                         current_user=self_display,
                         user_count=count,
                         member_items=member_items)

@app.route('/leave-room/<room_id>')
def leave_room(room_id):
    if "user" not in session:
        return redirect("/login")
    # 退出房间并返回首页
    return redirect("/")

# HTTP API路由已移除，改用Socket.IO实时通信

@app.route('/room-data/<id>')
def room_data(id):
    # 获取语音用户列表
    voice_users = []
    if id in socket_room_users:
        voice_users = list(socket_room_users[id].values())

    # 获取房间页面用户
    web_users = room_users.get(id, set())
    all_users = web_users | set(voice_users)
    count = len(all_users)

    # 生成member_items HTML
    profiles = get_user_profiles(all_users)
    member_items = ""
    for u in sorted(all_users):
        safe_u = u.replace("'", "").replace('"', "")
        label = format_user_label(u, profiles.get(u))
        info_link = f"<a class='user-info' href='/user/{safe_u}' onclick=\"event.stopPropagation();\">资料</a>"
        if u in voice_users:
            member_items += f"<li class='user-item voice' onclick=\"openVolumePanel('{safe_u}')\"><div class='user-main'><span class='badge badge-teal'>语音</span>{label}</div><div class='user-meta'>✅ {info_link}</div></li>"
        else:
            member_items += f"<li class='user-item online' onclick=\"openVolumePanel('{safe_u}')\"><div class='user-main'><span class='badge badge-gray'>在线</span>{label}</div><div class='user-meta'>• {info_link}</div></li>"

    return {"count": count, "members": member_items}

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

# ======================
# SocketIO事件处理器 - WebRTC信令
# ======================

# 存储房间内的用户信息
socket_room_users = {}  # {room_id: {sid: username}} - 语音房间用户

# 存储房间内的用户（访问房间页面的用户）
room_users = {}  # {room_id: set(username)} - 房间页面用户

# 存储用户名到sid的映射 {room_id: {username: sid}}
username_to_sid = {}

def get_realtime_stats():
    """获取实时统计数据"""
    online_users = 0
    active_rooms = 0
    
    # 统计语音房间用户
    for room_id, users in socket_room_users.items():
        online_users += len(users)
        active_rooms += 1
    
    return {
        'online_users': online_users,
        'active_rooms': active_rooms
    }

@socketio.on('connect')
def handle_connect():
    print(f'[DEBUG] Socket.IO连接成功 - SID: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'[DEBUG] Socket.IO断开连接 - SID: {request.sid}')
    # 清理房间信息
    for room_id in socket_room_users:
        if request.sid in socket_room_users[room_id]:
            username = socket_room_users[room_id][request.sid]
            del socket_room_users[room_id][request.sid]
            if room_id in username_to_sid and username in username_to_sid[room_id]:
                del username_to_sid[room_id][username]
            print(f'[DEBUG] 用户离开语音房间 - 房间: {room_id}, 用户: {username}')
            # 通知房间内其他用户
            emit('user_left', {'username': username}, room=room_id, skip_sid=request.sid)

@socketio.on('join_voice_room')
def handle_join_voice_room(data):
    room_id = data.get('room_id')
    username = data.get('username')

    print(f'[DEBUG] 收到join_voice_room - 房间: {room_id}, 用户: {username}, SID: {request.sid}')

    if not room_id or not username:
        print(f'[DEBUG] join_voice_room参数无效 - room_id: {room_id}, username: {username}')
        return

    # 加入SocketIO房间
    join_room(room_id)
    print(f'[DEBUG] 用户加入Socket.IO房间 - 房间: {room_id}')

    # 记录用户信息
    if room_id not in socket_room_users:
        socket_room_users[room_id] = {}
    if room_id not in username_to_sid:
        username_to_sid[room_id] = {}

    socket_room_users[room_id][request.sid] = username
    username_to_sid[room_id][username] = request.sid
    print(f'[DEBUG] 用户信息已记录 - SID: {request.sid}, 用户名: {username}')

    # 获取房间内现有用户
    existing_users = [u for sid, u in socket_room_users[room_id].items() if sid != request.sid]
    print(f'[DEBUG] 房间内现有用户: {existing_users}')

    # 通知房间内其他用户有新用户加入
    emit('user_joined', {'username': username}, room=room_id, skip_sid=request.sid)
    print(f'[DEBUG] 已通知其他用户新用户加入')

    # 发送现有用户列表给新用户
    emit('room_users', {'users': existing_users})
    print(f'[DEBUG] 已发送用户列表给新用户')

    print(f'用户 {username} 加入语音房间 {room_id}')

    # 查询用户ID用于日志记录（支持昵称和用户名）
    user_id = None
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM users WHERE nickname=%s OR username=%s", (username, username))
        result = cursor.fetchone()
        if result:
            user_id = result[0]
        db.close()
    except:
        pass

    # 记录加入语音房间日志
    log_user_action(
        user_id=user_id,
        username=username,
        action_type='start_voice',
        action_detail={'room_id': room_id},
        ip=request.remote_addr if hasattr(request, 'remote_addr') else None
    )

@socketio.on('leave_voice_room')
def handle_leave_voice_room(data):
    room_id = data.get('room_id')
    username = data.get('username')

    if room_id and username:
        # 清理房间信息
        if room_id in socket_room_users and request.sid in socket_room_users[room_id]:
            del socket_room_users[room_id][request.sid]
        if room_id in username_to_sid and username in username_to_sid[room_id]:
            del username_to_sid[room_id][username]

        # 离开SocketIO房间
        leave_room(room_id)

        # 通知房间内其他用户
        emit('user_left', {'username': username}, room=room_id)

        print(f'用户 {username} 离开语音房间 {room_id}')

        # 查询用户ID用于日志记录（支持昵称和用户名）
        user_id = None
        try:
            db = get_db_connection()
            cursor = db.cursor()
            # 先尝试按昵称查询，再按用户名查询
            cursor.execute("SELECT id FROM users WHERE nickname=%s OR username=%s", (username, username))
            result = cursor.fetchone()
            if result:
                user_id = result[0]
            db.close()
        except:
            pass

        # 记录离开语音房间日志
        log_user_action(
            user_id=user_id,
            username=username,
            action_type='stop_voice',
            action_detail={'room_id': room_id},
            ip=request.remote_addr if hasattr(request, 'remote_addr') else None
        )

@socketio.on('webrtc_offer')
def handle_webrtc_offer(data):
    target_username = data.get('target')
    offer = data.get('sdp')
    sender = data.get('sender')

    if target_username and offer and sender:
        # 通过用户名找到对应的sid
        target_sid = None
        for users in username_to_sid.values():
            if target_username in users:
                target_sid = users[target_username]
                break

        if target_sid:
            # 使用sid发送消息给特定用户
            emit('webrtc_offer', {'sdp': offer, 'sender': sender}, to=target_sid)
        else:
            print(f'警告: 找不到用户 {target_username} 的sid')

@socketio.on('webrtc_answer')
def handle_webrtc_answer(data):
    target_username = data.get('target')
    answer = data.get('sdp')
    sender = data.get('sender')

    if target_username and answer and sender:
        # 通过用户名找到对应的sid
        target_sid = None
        for users in username_to_sid.values():
            if target_username in users:
                target_sid = users[target_username]
                break

        if target_sid:
            emit('webrtc_answer', {'sdp': answer, 'sender': sender}, to=target_sid)
        else:
            print(f'警告: 找不到用户 {target_username} 的sid')

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    target_username = data.get('target')
    candidate = data.get('candidate')
    sender = data.get('sender')

    if target_username and candidate and sender:
        # 通过用户名找到对应的sid
        target_sid = None
        for users in username_to_sid.values():
            if target_username in users:
                target_sid = users[target_username]
                break

        if target_sid:
            emit('ice_candidate', {'candidate': candidate, 'sender': sender}, to=target_sid)
        else:
            print(f'警告: 找不到用户 {target_username} 的sid')

# ======================
# SocketIO事件处理器 - 文字聊天
# ======================

from utils.logger import log_user_action

@socketio.on('join_chat_room')
def handle_join_chat_room(data):
    room_id = data.get('room_id')
    username = data.get('username')

    if not room_id or not username:
        return

    # 加入SocketIO房间
    join_room(room_id)

    # 发送房间历史消息
    room = chat_rooms.get(room_id)
    if room is None:
        room = {"next_id": 1, "messages": []}
        chat_rooms[room_id] = room

    with chat_lock:
        msgs = room["messages"][-100:]  # 最近100条消息

    emit('chat_history', {'messages': msgs})

@socketio.on('send_chat_message')
def handle_send_chat_message(data):
    room_id = data.get('room_id')
    username = data.get('username')
    text = data.get('text')

    if not room_id or not username or not text:
        return

    text = str(text).strip()
    if not text:
        return
    if len(text) > 500:
        emit('chat_error', {'error': '消息过长'})
        return

    room = chat_rooms.get(room_id)
    if room is None:
        room = {"next_id": 1, "messages": []}
        chat_rooms[room_id] = room

    with chat_lock:
        msg_id = room["next_id"]
        room["next_id"] += 1
        msg = {
            "id": msg_id,
            "user": username,
            "text": text,
            "time": datetime.now().strftime('%H:%M')
        }
        room["messages"].append(msg)
        # 保持消息数量不超过1000条
        if len(room["messages"]) > 1000:
            room["messages"] = room["messages"][-1000:]

    # 广播消息给房间内所有用户
    emit('chat_message', msg, room=room_id)
    print(f'聊天消息: {username} 在房间 {room_id}: {text}')

    # 查询用户ID用于日志记录（支持昵称和用户名）
    user_id = None
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM users WHERE nickname=%s OR username=%s", (username, username))
        result = cursor.fetchone()
        if result:
            user_id = result[0]
        db.close()
    except:
        pass

    # 记录发送消息日志
    log_user_action(
        user_id=user_id,
        username=username,
        action_type='send_message',
        action_detail={'room_id': room_id, 'message': text},
        ip=request.remote_addr if hasattr(request, 'remote_addr') else None
    )

if __name__ == '__main__':
    import logging
    # 配置日志级别，只输出警告及以上级别的信息
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    logging.getLogger('engineio').setLevel(logging.ERROR)
    logging.getLogger('socketio').setLevel(logging.ERROR)
    logging.getLogger('geventwebsocket').setLevel(logging.ERROR)
    # 禁用Flask的访问日志
    import os
    os.environ['WERKZEUG_RUN_MAIN'] = 'true'
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True, log_output=False)
