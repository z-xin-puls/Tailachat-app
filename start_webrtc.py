"""
WebRTC版本启动脚本
只需要启动一个集成了SocketIO的Flask应用
"""
import subprocess
import sys
import os

def main():
    print("=" * 50)
    print("小T语音 - WebRTC版本启动")
    print("=" * 50)
    print("正在启动Web应用...")
    
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(current_dir, 'app.py')
    
    try:
        # 直接运行app.py
        subprocess.run([sys.executable, app_path])
    except KeyboardInterrupt:
        print("\n应用已停止")
    except Exception as e:
        print(f"启动失败: {e}")

if __name__ == '__main__':
    main()
