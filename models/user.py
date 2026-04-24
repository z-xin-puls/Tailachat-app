# 用户相关数据模型
import mysql.connector
import time
import threading
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
    """获取用户资料（带缓存）"""
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
            found = {r.get("username"): r for r in rows}
            with _user_profile_lock:
                for u in missing:
                    r = found.get(u) or {"username": u, "nickname": None, "avatar": None}
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
    
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        db.close()
        
        if result and result[0] == 'admin':
            return True
        return False
    except:
        return False

def get_user_role(username):
    """获取用户角色"""
    if not username:
        return 'user'
    
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        db.close()
        
        if result:
            return result[0]
        return 'user'
    except:
        return 'user'
