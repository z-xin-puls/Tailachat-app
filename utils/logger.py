# 用户行为日志记录工具
import json
from datetime import datetime
from models.database import get_db_connection

def log_user_action(user_id=None, username=None, action_type=None, action_detail=None, ip=None, user_agent=None):
    """
    记录用户行为日志

    Args:
        user_id: 用户ID（可选）
        username: 用户名（可选）
        action_type: 操作类型（必填）
            - login: 用户登录
            - logout: 用户登出
            - register: 用户注册
            - create_room: 创建房间
            - join_room: 加入房间
            - leave_room: 离开房间
            - send_message: 发送消息
            - start_voice: 启动语音
            - stop_voice: 停止语音
            - upload_avatar: 上传头像
            - update_profile: 更新资料
        action_detail: 操作详情（字典，会被转为JSON存储）
        ip: IP地址
        user_agent: 用户代理
    """
    try:
        db = get_db_connection()
        cursor = db.cursor()

        # 将action_detail字典转为JSON字符串
        detail_json = json.dumps(action_detail) if action_detail else None

        # 记录到user_log表（保持兼容性）
        cursor.execute("""
            INSERT INTO user_log (user_id, username, action_type, action_detail, ip, user_agent, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, username, action_type, detail_json, ip, user_agent, datetime.now()))

        # 记录到user_activity表（用于统计分析）
        # 先检查用户是否存在（支持username和nickname）
        if username:
            cursor.execute("SELECT username FROM users WHERE username = %s OR nickname = %s", (username, username))
            result = cursor.fetchone()
            if result:
                # 使用数据库中的真实username
                real_username = result[0]
                cursor.execute("""
                    INSERT INTO user_activity (username, action, ip)
                    VALUES (%s, %s, %s)
                """, (real_username, action_type, ip))
            else:
                print(f"用户 {username} 不存在于users表，跳过记录到user_activity")

        db.commit()
        db.close()
        return True
    except Exception as e:
        print(f"记录用户行为日志失败: {e}")
        try:
            db.close()
        except:
            pass
        return False
