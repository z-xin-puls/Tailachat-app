
import socket
import json
import threading
import sys
import base64
import hashlib
import struct

# ======================
# WebSocket 文字聊天客户端
# ======================
CHAT_HOST = '127.0.0.1'
CHAT_PORT = 8888

def create_websocket_handshake():
    """创建 WebSocket 握手请求"""
    key = base64.b64encode(b'client_key_12345678').decode()
    request = f"GET / HTTP/1.1\r\n"
    request += f"Host: {CHAT_HOST}:{CHAT_PORT}\r\n"
    request += "Upgrade: websocket\r\n"
    request += "Connection: Upgrade\r\n"
    request += f"Sec-WebSocket-Key: {key}\r\n"
    request += "Sec-WebSocket-Version: 13\r\n"
    request += "\r\n"
    return request.encode()

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
        payload_len = struct.unpack('>H', data[offset:offset+2])[0]
        offset += 2
    elif payload_len == 127:
        if len(data) < offset + 8:
            return None, None
        payload_len = struct.unpack('>Q', data[offset:offset+8])[0]
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
        frame.extend(struct.pack('>H', payload_len))
    else:
        frame.append(127)
        frame.extend(struct.pack('>Q', payload_len))

    # 添加负载数据
    frame.extend(data)

    return bytes(frame)

def receive_messages(sock, username):
    """接收并显示消息"""
    buffer = b''
    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buffer += chunk

            opcode, data = parse_websocket_frame(buffer)
            while data is not None:
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
                        msg = json.loads(data.decode('utf-8'))
                        print(f"\r[{msg['time']}] {msg['user']}: {msg['message']}")
                        print(f"\r{username}> ", end='', flush=True)
                    except:
                        pass
                elif opcode == 0x8:  # 关闭帧
                    return

                # 尝试解析下一个帧
                opcode, data = parse_websocket_frame(buffer)
        except:
            break
    print("\n已断开连接")
    sock.close()

def send_messages(sock, username):
    """发送消息"""
    while True:
        try:
            msg = input(f"{username}> ")
            if msg.lower() == 'quit':
                # 发送关闭帧
                close_frame = create_websocket_frame(b'', opcode=0x8)
                sock.sendall(close_frame)
                break
            frame = create_websocket_frame(msg.encode('utf-8'))
            sock.sendall(frame)
        except:
            break
    sock.close()
    sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: python chat_client.py <用户名> <房间ID>")
        sys.exit(1)

    username = sys.argv[1]
    room_id = sys.argv[2]

    # 连接服务器
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((CHAT_HOST, CHAT_PORT))

    # 发送 WebSocket 握手请求
    handshake = create_websocket_handshake()
    sock.sendall(handshake)

    # 接收握手响应
    response = sock.recv(4096).decode('utf-8')
    if '101 Switching Protocols' not in response:
        print("WebSocket 握手失败")
        sock.close()
        sys.exit(1)

    # 发送认证信息
    auth_info = {
        'username': username,
        'room_id': room_id
    }
    auth_frame = create_websocket_frame(json.dumps(auth_info).encode('utf-8'))
    sock.sendall(auth_frame)

    print(f"💬 已加入房间 {room_id}")
    print("输入 'quit' 退出聊天")

    # 启动接收消息线程
    receive_thread = threading.Thread(target=receive_messages, args=(sock, username), daemon=True)
    receive_thread.start()

    # 发送消息
    send_messages(sock, username)
