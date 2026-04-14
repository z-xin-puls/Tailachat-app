import socket
import sounddevice as sd
import numpy as np
import threading
import sys
import time
import json

# 运行状态标志
running = True

mic_gain = 1.0
playback_gains = {}
gain_lock = threading.Lock()

# ======================
# TCP消息处理函数（解决粘包问题）
# ======================
def recv_exact(sock, size):
    """精确接收指定长度的数据"""
    data = b''
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            return None
        data += packet
    return data

def recv_message(sock):
    """接收完整的消息（带长度前缀）"""
    # 先接收4字节的长度前缀
    length_data = recv_exact(sock, 4)
    if not length_data:
        return None

    # 解析长度
    length = int.from_bytes(length_data, byteorder='big')

    # 接收消息体
    message = recv_exact(sock, length)
    return message

def send_message(sock, data):
    """发送完整的消息（带长度前缀）"""
    # 添加4字节的长度前缀
    length = len(data)
    length_data = length.to_bytes(4, byteorder='big')
    sock.sendall(length_data + data)

# 超低延迟优化配置
HOST = '127.0.0.1'
PORT = 9999
FORMAT = 'int16'
CHANNELS = 1
RATE = 32000  # 降低一点，减少网络压力
CHUNK = 512   # 更小的块 = 更低延迟

# 从命令行获取用户名和房间ID
import sys
if len(sys.argv) < 3:
    print("请提供用户名和房间ID！用法: python client.py <用户名> <房间ID>")
    sys.exit(1)
USERNAME = sys.argv[1]
ROOM_ID = sys.argv[2]
CONTROL_PORT = int(sys.argv[3]) if len(sys.argv) >= 4 else 0

# 连接服务器
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))

# 发送用户名和房间ID给服务器（格式: "username|room_id"）
try:
    auth_data = f"{USERNAME}|{ROOM_ID}"
    send_message(client_socket, auth_data.encode('utf-8'))
    print(f"{USERNAME} 已加入房间：{ROOM_ID}")
except Exception as e:
    print(f"[ERR] 发送认证信息失败：{e}")
    sys.exit(1)

# 音频缓冲（解决卡顿核心）
audio_buffer = bytearray()
buffer_lock = threading.Lock()
sender_buffer = bytearray()

def clamp_int16(x):
    return np.clip(x, -32768, 32767).astype(np.int16)

def apply_gain_int16(audio_int16, gain):
    if gain == 1.0:
        return audio_int16
    scaled = audio_int16.astype(np.float32) * float(gain)
    return clamp_int16(scaled)

def parse_packet(packet):
    if not packet:
        return None, None
    name_len = packet[0]
    if len(packet) < 1 + name_len:
        return None, None
    sender = packet[1:1 + name_len].decode('utf-8', errors='ignore') if name_len else ""
    audio_bytes = packet[1 + name_len:]
    return sender, audio_bytes

def handle_control_conn(conn):
    try:
        data = b""
        while b"\n" not in data and len(data) < 8192:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
        line = data.split(b"\n", 1)[0].strip()
        payload = json.loads(line.decode('utf-8')) if line else {}
        global mic_gain
        with gain_lock:
            if payload.get("type") == "mic":
                try:
                    mic_gain = float(payload.get("gain", 1.0))
                except:
                    mic_gain = 1.0
                mic_gain = max(0.0, min(2.0, mic_gain))
            elif payload.get("type") == "playback":
                target = str(payload.get("target", ""))
                try:
                    gain = float(payload.get("gain", 1.0))
                except:
                    gain = 1.0
                gain = max(0.0, min(2.0, gain))
                if target:
                    playback_gains[target] = gain
        conn.sendall(b"OK\n")
    except:
        try:
            conn.sendall(b"ERR\n")
        except:
            pass
    finally:
        try:
            conn.close()
        except:
            pass

def control_server():
    if CONTROL_PORT <= 0:
        return
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('127.0.0.1', CONTROL_PORT))
    srv.listen(5)
    while running:
        try:
            conn, _ = srv.accept()
        except:
            break
        threading.Thread(target=handle_control_conn, args=(conn,), daemon=True).start()
    try:
        srv.close()
    except:
        pass

# ---------------------- 录音并发送（无溢出） ----------------------
def record():
    global running
    stream = sd.InputStream(
        samplerate=RATE,
        channels=CHANNELS,
        dtype=FORMAT,
        blocksize=CHUNK
    )
    stream.start()

    try:
        while running:
            data, overflow = stream.read(CHUNK)
            if not overflow:
                try:
                    with gain_lock:
                        g = mic_gain
                    audio = np.array(data, copy=False)
                    audio = audio.reshape(-1)
                    audio = apply_gain_int16(audio, g)
                    send_message(client_socket, audio.tobytes())
                except (ConnectionError, OSError) as e:
                    print(f"[WARN] 发送失败：{e}")
                    break
    except Exception as e:
        print(f"[WARN] 录音异常：{e}")
    finally:
        stream.stop()
        stream.close()
        print("[OK] 录音流已关闭")

# ---------------------- 接收并播放（流畅不卡） ----------------------
def play():
    global running, audio_buffer, sender_buffer

    stream = sd.OutputStream(
        samplerate=RATE,
        channels=CHANNELS,
        dtype=FORMAT,
        blocksize=CHUNK
    )
    stream.start()

    try:
        while running:
            try:
                packet = recv_message(client_socket)
                if not packet:
                    print("[WARN] 服务器断开连接")
                    break
                sender, audio_bytes = parse_packet(packet)
                if audio_bytes is None:
                    continue
                with gain_lock:
                    g = playback_gains.get(sender, 1.0)
                audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
                audio_int16 = apply_gain_int16(audio_int16, g)

                with buffer_lock:
                    audio_buffer.extend(audio_int16.tobytes())

                    while len(audio_buffer) >= CHUNK * 2:
                        frame = audio_buffer[:CHUNK * 2]
                        del audio_buffer[:CHUNK * 2]
                        stream.write(np.frombuffer(frame, dtype=np.int16))
            except (ConnectionError, OSError) as e:
                print(f"[WARN] 接收失败：{e}")
                break
    except Exception as e:
        print(f"[WARN] 播放异常：{e}")
    finally:
        stream.stop()
        stream.close()
        print("[OK] 播放流已关闭")

# ---------------------- 启动线程 ----------------------
print("小T语音【流畅低延迟版】已连接！")
print("按 Ctrl+C 退出程序")

if CONTROL_PORT > 0:
    threading.Thread(target=control_server, daemon=True).start()

record_thread = threading.Thread(target=record, daemon=True)
play_thread = threading.Thread(target=play, daemon=True)

record_thread.start()
play_thread.start()

# 保持运行
try:
    while running:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("正在退出...")
    running = False

    # 等待线程结束
    record_thread.join(timeout=2)
    play_thread.join(timeout=2)

    # 关闭socket连接
    try:
        client_socket.close()
        print("[OK] 已断开连接")
    except:
        pass

    print("程序已退出")
    sys.exit(0)
