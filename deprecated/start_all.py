import subprocess
import sys
import time
import os

def run_service(script_name, description):
    """运行服务"""
    try:
        print(f"🚀 启动 {description}...")

        # 拿到当前 start_all.py 所在的文件夹
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 拼接出完整路径
        script_path = os.path.join(current_dir, script_name)

        process = subprocess.Popen([sys.executable, script_path])
        return process
    except Exception as e:
        print(f"❌ 启动 {description} 失败: {e}")
        return None

if __name__ == '__main__':
    print("=" * 50)
    print("小T语音 - 启动所有服务")
    print("=" * 50)

    # 启动语音服务器
    voice_server = run_service('server.py', '语音服务器')
    time.sleep(1)

    # 启动聊天服务器
    chat_server = run_service('chat_server.py', '聊天服务器')
    time.sleep(1)

    # 启动 Web 应用
    web_app = run_service('app.py', 'Web 应用')

    print("=" * 50)
    print("✅ 所有服务已启动！")
    print("=" * 50)
    print("🎤 语音服务器: 端口 9999")
    print("💬 聊天服务器: 端口 8888")
    print("🌐 Web 应用: http://127.0.0.1:5000")
    print("=" * 50)
    print("按 Ctrl+C 停止所有服务")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止所有服务...")

        # 停止所有服务
        for process in [voice_server, chat_server, web_app]:
            if process:
                process.terminate()

        print("✅ 所有服务已停止")