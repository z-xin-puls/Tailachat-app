
import socket
import threading
import json
import base64
import hashlib
from datetime import datetime

# ======================
# WebSocket 文字聊天服务器
# ======================
CHAT_HOST = '0.0.0.0'
CHAT_PORT = 8888

# 房间和用户管理
chat_rooms = {}  # {room_id: [conn1, conn2, ...]}
room_messages = {}  # {room_id: [{'user': 'xxx', 'message': 'xxx', 'time': 'xxx'}, ...]}
room_lock = threading.Lock()

def create_handshake_response(key):
    """创建 WebSocket 握手响应"""
    magic_string = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    accept_key = base64.b64encode(hashlib.sha1((key + magic_string).encode()).digest()).decode()
    response = f"HTTP/1.1 101 Switching Protocols\r\n"
    response += "Upgrade: websocket\r\n"
    response += "Connection: Upgrade\r\n"
    response += f"Sec-WebSocket-Accept: {accept_key}\r\n"
    response += "\r\n"
    return response.encode()

def parse_websocket_frame(data):
    """解析 WebSocket 帧"""
    if len(data) < 2:
        return None, None

    first_byte = data[0]
    second_byte = data[1]

    fin = (first_byte & 0x80) != 0
    opcode = first_byte & 0x0F
    masked = (second_byte & 0x80) != 0
    payload_len = second_byte & 0x7F

    offset = 2

    # 处理扩展长度
    if payload_len == 126:
        if len(data) < offset + 2:
            return None, None
        payload_len = int.from_bytes(data[offset:offset+2], byteorder='big')
        offset += 2
    elif payload_len == 127:
        if len(data) < offset + 8:
            return None, None
        payload_len = int.from_bytes(data[offset:offset+8], byteorder='big')
        offset += 8

    # 获取掩码
    masking_key = None
    if masked:
        if len(data) < offset + 4:
            return None, None
        masking_key = data[offset:offset+4]
        offset += 4

    # 获取负载数据
    if len(data) < offset + payload_len:
        return None, None

    payload = data[offset:offset+payload_len]

    # 解码负载数据
    if masked:
        decoded = bytearray(payload_len)
        for i in range(payload_len):
            decoded[i] = payload[i] ^ masking_key[i % 4]
        payload = bytes(decoded)

    return opcode, payload

def create_websocket_frame(data, opcode=0x1):
    """创建 WebSocket 帧"""
    frame = bytearray()

    # 设置 FIN 和 opcode
    first_byte = 0x80 | opcode
    frame.append(first_byte)

    # 设置 MASK 和 payload 长度
    payload_len = len(data)
    if payload_len < 126:
        frame.append(payload_len)
    elif payload_len < 65536:
        frame.append(126)
        frame.extend(payload_len.to_bytes(2, byteorder='big'))
    else:
        frame.append(127)
        frame.extend(payload_len.to_bytes(8, byteorder='big'))

    # 添加负载数据
    frame.extend(data)

    return bytes(frame)

def broadcast_message(room_id, message_data):
    """向房间内所有用户广播消息"""
    with room_lock:
        if room_id in chat_rooms:
            # 保存消息历史
            if room_id not in room_messages:
                room_messages[room_id] = []
            room_messages[room_id].append(message_data)
            # 只保留最近100条消息
            if len(room_messages[room_id]) > 100:
                room_messages[room_id] = room_messages[room_id][-100:]

            # 广播消息
            for conn in chat_rooms[room_id].copy():
                try:
                    frame = create_websocket_frame(json.dumps(message_data).encode('utf-8'))
                    conn.sendall(frame)
                except:
                    chat_rooms[room_id].remove(conn)

def handle_client(conn, addr):
    """处理客户端连接"""
    try:
        # 接收 WebSocket 握手请求
        request = b''
        while True:
            chunk = conn.recv(1024)
            if not chunk:
                conn.close()
                return
            request += chunk
            if b'\r\n\r\n' in request:
                break

        # 解析 Sec-WebSocket-Key
        request_text = request.decode('utf-8')
        lines = request_text.split('\r\n')
        ws_key = None
        for line in lines:
            if line.lower().startswith('sec-websocket-key:'):
                ws_key = line.split(':', 1)[1].strip()
                break

        if not ws_key:
            conn.close()
            return

        # 发送握手响应
        response = create_handshake_response(ws_key)
        conn.sendall(response)

        # 接收第一条消息（认证信息）
        opcode, auth_data = parse_websocket_frame(b'')
        buffer = b''
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                conn.close()
                return
            buffer += chunk
            opcode, auth_data = parse_websocket_frame(buffer)
            if auth_data is not None:
                # 移除已处理的数据
                frame_size = len(auth_data)
                # 计算帧的总大小（包括头部）
                if len(buffer) >= 2:
                    payload_len = buffer[1] & 0x7F
                    header_size = 2
                    if payload_len == 126:
                        header_size += 2
                    elif payload_len == 127:
                        header_size += 8
                    if buffer[1] & 0x80:
                        header_size += 4
                    frame_size = header_size + payload_len
                buffer = buffer[frame_size:]
                break

        if not auth_data:
            conn.close()
            return

        auth_info = json.loads(auth_data.decode('utf-8'))
        username = auth_info['username']
        room_id = auth_info['room_id']

        # 加入房间
        with room_lock:
            if room_id not in chat_rooms:
                chat_rooms[room_id] = []
            chat_rooms[room_id].append(conn)

        print(f"💬 用户 {username} 加入文字聊天房间 {room_id}")

        # 发送历史消息
        with room_lock:
            if room_id in room_messages:
                for msg in room_messages[room_id]:
                    try:
                        frame = create_websocket_frame(json.dumps(msg).encode('utf-8'))
                        conn.sendall(frame)
                    except:
                        pass

        # 处理消息
        while True:
            opcode, data = parse_websocket_frame(buffer)
            if data is not None:
                # 移除已处理的数据
                frame_size = len(data)
                if len(buffer) >= 2:
                    payload_len = buffer[1] & 0x7F
                    header_size = 2
                    if payload_len == 126:
                        header_size += 2
                    elif payload_len == 127:
                        header_size += 8
                    if buffer[1] & 0x80:
                        header_size += 4
                    frame_size = header_size + payload_len
                buffer = buffer[frame_size:]

                # 处理文本消息
                if opcode == 0x1:  # 文本帧
                    try:
                        message = data.decode('utf-8')
                        message_data = {
                            'user': username,
                            'message': message,
                            'time': datetime.now().strftime('%H:%M:%S')
                        }
                        broadcast_message(room_id, message_data)
                    except:
                        pass
                elif opcode == 0x8:  # 关闭帧
                    break
            else:
                # 接收更多数据
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buffer += chunk
    except Exception as e:
        print(f"客户端处理异常: {e}")
    finally:
        # 清理连接
        with room_lock:
            if room_id in chat_rooms and conn in chat_rooms[room_id]:
                chat_rooms[room_id].remove(conn)
                if not chat_rooms[room_id]:
                    del chat_rooms[room_id]
        conn.close()
        print(f"💬 用户 {username} 离开文字聊天房间 {room_id}")

def start_chat_server():
    """启动 WebSocket 文字聊天服务器"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((CHAT_HOST, CHAT_PORT))
    server.listen(10)

    print(f"💬 WebSocket 文字聊天服务器已启动，监听端口 {CHAT_PORT}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == '__main__':
    start_chat_server()
