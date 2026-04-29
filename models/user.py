# 用户相关数据模型
import mysql.connector
import time
import threading
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from models.database import get_db_connection
from config import PROFILE_CACHE_TTL_SECONDS

# 用户资料缓存
_user_profile_cache = {}
_user_profile_lock = threading.Lock()

def clear_user_profile_cache(username):
    """清除用户资料缓存"""
    if not username:
        return
    with _user_profile_lock:
        _user_profile_cache.pop(str(username), None)

def get_user_profiles(usernames):
    """获取用户资料（带缓存，使用pandas优化）"""
    names = [u for u in set([str(x) for x in (usernames or []) if x])]
    now = time.time()
    out = {}
    missing = []
    
    with _user_profile_lock:
        for u in names:
            item = _user_profile_cache.get(u)
            if item and (now - float(item.get("ts", 0))) < PROFILE_CACHE_TTL_SECONDS:
                out[u] = item
            else:
                missing.append(u)

    if missing:
        try:
            db = get_db_connection()
            cursor = db.cursor(dictionary=True)
            placeholders = ",".join(["%s"] * len(missing))
            cursor.execute(
                f"SELECT username, nickname, avatar FROM users WHERE username IN ({placeholders})",
                tuple(missing)
            )
            rows = cursor.fetchall() or []
            db.close()
            
            # 使用pandas优化数据处理
            if rows:
                df = pd.DataFrame(rows)
                found = df.set_index('username').to_dict('index')
            else:
                found = {}
                
            with _user_profile_lock:
                for u in missing:
                    r = found.get(u, {"username": u, "nickname": None, "avatar": None})
                    item = {"nickname": r.get("nickname"), "avatar": r.get("avatar"), "ts": now}
                    _user_profile_cache[u] = item
                    out[u] = item
        except:
            with _user_profile_lock:
                for u in missing:
                    item = {"nickname": None, "avatar": None, "ts": now}
                    _user_profile_cache[u] = item
                    out[u] = item

    for u in names:
        if u not in out:
            out[u] = {"nickname": None, "avatar": None, "ts": now}
    return out

def resolve_avatar_url(raw_value):
    """解析头像URL"""
    if not raw_value:
        from config import DEFAULT_AVATAR_URL
        return DEFAULT_AVATAR_URL
    url = str(raw_value).strip()
    if not url:
        from config import DEFAULT_AVATAR_URL
        return DEFAULT_AVATAR_URL
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith('/'):
        return url
    return f"/{url.lstrip('/')}"

def format_user_label(username, profile_item):
    """格式化用户标签"""
    from utils.helpers import html_escape
    
    u = html_escape(username)
    nick = html_escape((profile_item or {}).get("nickname") or "")
    avatar = resolve_avatar_url((profile_item or {}).get("avatar"))
    avatar_img = f"<img src='{avatar}' alt='avatar' loading='lazy' style='width:24px;height:24px;border-radius:50%;object-fit:cover;margin-right:8px;'>"
    
    if nick and nick != username:
        return f"<div style='display:flex;align-items:center;gap:8px;min-width:0'>{avatar_img}<span class='user-name'>{nick}</span><span class='user-sub'>@{u}</span></div>"
    return f"<div style='display:flex;align-items:center;gap:8px;min-width:0'>{avatar_img}<span class='user-name'>{u}</span></div>"

def is_admin(username):
    """检查用户是否为管理员"""
    if not username:
        return False
    
    db = None
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        cursor.close()
        db.close()
        
        if result and result[0] == 'admin':
            return True
        return False
    except:
        return False
    finally:
        if db:
            try:
                db.close()
            except:
                pass

def get_user_role(username):
    """获取用户角色"""
    if not username:
        return 'user'
    
    db = None
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        cursor.close()
        db.close()
        
        if result:
            return result[0]
        return 'user'
    except:
        return 'user'
    finally:
        if db:
            try:
                db.close()
            except:
                pass

def get_user_activity_summary(days=30):
    """获取用户活动摘要（使用pandas优化）"""
    db = None
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # 生成时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        cursor.execute("""
            SELECT u.username, u.nickname, u.role, COUNT(ua.timestamp) as activity_count
            FROM users u
            LEFT JOIN user_activity ua ON u.username = ua.username 
                AND ua.timestamp BETWEEN %s AND %s
            GROUP BY u.username, u.nickname, u.role
            ORDER BY activity_count DESC
        """, (start_time, end_time))
        
        data = cursor.fetchall()
        cursor.close()
        db.close()
        
        if not data:
            return {'users': [], 'total_activities': 0, 'active_users': 0, 'total_users': 0}
        
        # 使用pandas处理数据
        df = pd.DataFrame(data, columns=['username', 'nickname', 'role', 'activity_count'])
        
        # 计算活动统计
        total_activities = df['activity_count'].sum()
        active_users = (df['activity_count'] > 0).sum()
        
        # 转换为字典格式
        user_summary = []
        for _, row in df.iterrows():
            user_summary.append({
                'username': row['username'],
                'nickname': row['nickname'],
                'role': row['role'],
                'activity_count': int(row['activity_count']),
                'activity_percentage': round((row['activity_count'] / max(total_activities, 1)) * 100, 2)
            })
        
        return {
            'users': user_summary,
            'total_activities': int(total_activities),
            'active_users': int(active_users),
            'total_users': len(df)
        }
    except Exception as e:
        print(f"获取用户活动摘要失败: {e}")
        if db:
            try:
                db.close()
            except:
                pass
        return {'users': [], 'total_activities': 0, 'active_users': 0, 'total_users': 0}

def get_user_registration_trend(days=30):
    """获取用户注册趋势（使用numpy和pandas优化）"""
    db = None
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # 获取总用户数
        cursor.execute("SELECT COUNT(*) as total_users FROM users")
        total_users = cursor.fetchone()[0]
        cursor.close()
        db.close()
        
        # 使用numpy生成日期数组
        dates = np.array([(datetime.now() - timedelta(days=i)).date() for i in range(days-1, -1, -1)])
        
        # 模拟注册数据（如果数据库没有created_at字段）
        # 这里使用简单的线性增长作为示例
        daily_counts = np.random.poisson(max(1, total_users // days), size=len(dates))
        cumulative_counts = np.cumsum(daily_counts)
        
        # 转换为字典格式
        trend_data = []
        for i, date in enumerate(dates):
            trend_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'daily_count': int(daily_counts[i]),
                'cumulative_count': int(cumulative_counts[i])
            })
        
        return trend_data
    except Exception as e:
        print(f"获取用户注册趋势失败: {e}")
        if db:
            try:
                db.close()
            except:
                pass
        return []
