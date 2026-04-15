import socket
import threading
import mysql.connector
import time
from datetime import datetime
from flask import Flask, jsonify

# 创建Flask应用，用于提供API接口
api_app = Flask(__name__)


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root", 
    "database": "voice_chat"
}


def recv_exact(conn, size):
    data = b''
    while len(data) < size:
        packet = conn.recv(size - len(data))
        if not packet:
            return None
        data += packet
    return data

def recv_message(conn):
    """接收完整的消息（带长度前缀）"""
    # 先接收4字节的长度前缀
    length_data = recv_exact(conn, 4)
    if not length_data:
        return None

    # 解析长度
    length = int.from_bytes(length_data, byteorder='big')

    # 接收消息体
    message = recv_exact(conn, length)
    return message

def send_message(conn, data):
    """发送完整的消息（带长度前缀）"""
    # 添加4字节的长度前缀
    length = len(data)
    length_data = length.to_bytes(4, byteorder='big')
    conn.sendall(length_data + data)

# ======================
# 【数据库日志】记录用户连接（安全版，不崩服务器）
# ======================
def log_user_connection(ip):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_log (ip, connect_time) VALUES (%s, %s)",
            (ip, datetime.now())
        )
        conn.commit()
        cursor.close()
        conn.close()
        print(f"[OK] 已记录用户：{ip}")
    except Exception as e:
        # 就算数据库挂了，也不影响语音！
        print(f"[WARN] 日志记录失败（不影响语音）：{e}")

# ======================
# 【语音服务】稳定版
# ======================
HOST = '0.0.0.0'
PORT = 9999

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen(10)

# 房间管理
room_clients = {}  # {room_id: [client1, client2, ...]}
room_lock = threading.Lock()  # 线程锁，保证线程安全

# 用户身份管理 {conn: {'username': 'xxx', 'room_id': 'xxx'}}
client_info = {}

# 正在说话的用户状态 {room_id: {'username': 'xxx', 'last_speak_time': timestamp}}
speaking_users = {}
speaking_lock = threading.Lock()

# 向指定房间广播声音（跳过发送者）
def broadcast_to_room(room_id, data, sender_conn=None):
    # 更新正在说话的用户状态
    if sender_conn and sender_conn in client_info:
        username = client_info[sender_conn]['username']
        with speaking_lock:
            speaking_users[room_id] = {
                'username': username,
                'last_speak_time': time.time()
            }

    username_bytes = b""
    if sender_conn and sender_conn in client_info:
        try:
            username_bytes = client_info[sender_conn]['username'].encode('utf-8')
        except:
            username_bytes = b""
    if len(username_bytes) > 255:
        username_bytes = username_bytes[:255]
    packet = bytes([len(username_bytes)]) + username_bytes + data

    with room_lock:
        if room_id not in room_clients:
            return
        for c in room_clients[room_id].copy():
            # 跳过发送者，避免回音
            if c is sender_conn:
                continue
            try:
                send_message(c, packet)
            except:
                room_clients[room_id].remove(c)

# 处理客户端连接
def handle_client(conn, addr):
    ip = str(addr)
    # 独立线程记录日志，绝不卡语音！
    threading.Thread(target=log_user_connection, args=(ip,), daemon=True).start()

    print(f"[OK] 用户连接：{ip}")

    # 首先接收用户名和房间ID
    try:
        # 接收格式: "username|room_id"
        auth_data = recv_message(conn)
        if not auth_data:
            conn.close()
            print(f"[ERR] 用户 {ip} 连接失败")
            return
        auth_text = auth_data.decode('utf-8')
        username, room_id = auth_text.split('|', 1)
        print(f"[ROOM] 用户 {username} ({ip}) 加入房间：{room_id}")
    except Exception as e:
        conn.close()
        print(f"[ERR] 用户 {ip} 认证失败：{e}")
        return

    # 将客户端加入对应房间
    with room_lock:
        if room_id not in room_clients:
            room_clients[room_id] = []
        room_clients[room_id].append(conn)

        # 存储用户信息
        client_info[conn] = {'username': username, 'room_id': room_id}

    try:
        while True:
            data = recv_message(conn)
            if not data:
                break
            broadcast_to_room(room_id, data, sender_conn=conn)
    except:
        pass
    finally:
        # 从房间中移除客户端
        with room_lock:
            if room_id in room_clients and conn in room_clients[room_id]:
                room_clients[room_id].remove(conn)
                # 如果房间为空，删除房间
                if not room_clients[room_id]:
                    del room_clients[room_id]

            # 清理用户信息
            if conn in client_info:
                username = client_info[conn]['username']
                del client_info[conn]
                print(f"[INFO] 用户 {username} ({ip}) 离开房间 {room_id}")
            else:
                print(f"[INFO] 用户 {ip} 离开房间 {room_id}")

        conn.close()

# ======================
# API路由
# ======================
@api_app.route('/api/room-users/<room_id>')
def get_room_users(room_id):
    """获取指定语音房间的在线用户列表"""
    with room_lock:
        if room_id not in room_clients:
            return jsonify({"users": [], "speaking": None})

        users = []
        for conn in room_clients[room_id]:
            if conn in client_info:
                users.append(client_info[conn]['username'])

    # 获取正在说话的用户
    speaking_user = None
    with speaking_lock:
        if room_id in speaking_users:
            # 检查是否在最近2秒内说话
            if time.time() - speaking_users[room_id]['last_speak_time'] < 2.0:
                speaking_user = speaking_users[room_id]['username']
            else:
                # 超过2秒，清除正在说话状态
                del speaking_users[room_id]

    return jsonify({"users": users, "speaking": speaking_user})

@api_app.route('/api/all-rooms')
def get_all_rooms():
    """获取所有语音房间及其在线用户"""
    with room_lock:
        rooms = {}
        for room_id, clients in room_clients.items():
            rooms[room_id] = []
            for conn in clients:
                if conn in client_info:
                    rooms[room_id].append(client_info[conn]['username'])

        return jsonify(rooms)

# ======================
# 启动服务器
# ======================
print("小T语音服务器（已启用数据库日志）")
print("等待用户连接...")

# 在单独的线程中启动Flask API服务器
def run_api():
    import logging
    # 配置日志级别，只输出警告及以上级别的信息
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.WARNING)
    # 绑定到0.0.0.0以便在Railway中可访问
    api_app.run(host='0.0.0.0', port=5001, debug=False)

api_thread = threading.Thread(target=run_api, daemon=True)
api_thread.start()
print("API服务器已启动在端口 5001")

while True:
    conn, addr = server.accept()
    threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
