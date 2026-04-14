# 个人中心路由
from flask import Blueprint, request, redirect, render_template_string, session, send_from_directory
from models.database import get_db_connection
from models.user import get_user_profiles, clear_user_profile_cache, resolve_avatar_url
from utils.helpers import html_escape
from config import DEFAULT_AVATARS, ALLOWED_IMAGE_EXTS, AVATAR_DIR
import os
from datetime import datetime

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/avatars/<path:filename>')
def serve_avatar(filename):
    return send_from_directory(AVATAR_DIR, filename)

@profile_bp.route('/profile', methods=['GET','POST'])
def profile():
    if "user" not in session:
        return redirect("/login")
    username = session["user"]

    if request.method == "POST":
        nickname = request.form.get("nickname", "").strip()
        if len(nickname) > 30:
            return "<h3>昵称不能超过30个字符</h3>"

        db = get_db_connection()
        cursor = db.cursor()
        if nickname:
            cursor.execute("UPDATE users SET nickname=%s WHERE username=%s", (nickname, username))
        db.commit()
        db.close()
        clear_user_profile_cache(username)

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT username, nickname, avatar FROM users WHERE username=%s", (username,))
    me = cursor.fetchone()
    db.close()
    nick = (me.get("nickname") or "").strip() if me else ""
    avatar = resolve_avatar_url(me.get("avatar")) if me else resolve_avatar_url(None)
    display = nick if nick else username

    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>泰拉通讯 - 个人中心</title>
        <style>
            *{{margin:0;padding:0;box-sizing:border-box}}
            body{{background:#0a0a0f url('/static/images/namecard/nc_taiko/bg.png') center/cover no-repeat fixed;color:#e5e7eb;font-family:Segoe UI,微软雅黑;min-height:100vh;position:relative;overflow:hidden}}
            a{{text-decoration:none;color:#FF5555}}
            .user-info{{position:fixed;bottom:30px;right:30px;display:flex;align-items:center;gap:16px;z-index:10}}
            .avatar{{width:80px;height:80px;border-radius:12px;border:3px solid rgba(255,85,85,0.5);display:flex;align-items:center;justify-content:center;background:rgba(26,16,37,0.8);overflow:hidden;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,0.4),0 0 20px rgba(255,85,85,0.2);backdrop-filter:blur(10px)}}
            .avatar img{{width:100%;height:100%;object-fit:cover}}
            .username{{color:#FF5555;font-size:18px;font-weight:900;text-shadow:0 2px 8px rgba(0,0,0,0.5)}}
            .sidebar{{position:fixed;top:0;right:0;width:500px;height:100vh;background:transparent;border:none;transform:translateX(100%);transition:transform 0.4s cubic-bezier(0.4,0,0.2,1);z-index:1000;backdrop-filter:none;box-shadow:none}}
            .sidebar.active{{transform:translateX(0)}}
            .sidebar-toggle{{position:fixed;top:50%;right:20px;transform:translateY(-50%);width:50px;height:50px;background:rgba(255,85,85,0.3);color:#FF5555;border:1px solid rgba(255,85,85,0.5);border-radius:12px;cursor:pointer;font-size:24px;font-weight:900;display:flex;align-items:center;justify-content:center;z-index:999;backdrop-filter:blur(10px);transition:all 0.3s ease}}
            .sidebar-toggle:hover{{background:rgba(255,85,85,0.5);border-color:rgba(255,85,85,0.8)}}
            .sidebar-toggle.active{{transform:translateY(-50%) rotate(180deg)}}
            .sidebar-content{{padding:32px;overflow-y:auto;height:100vh}}
            .sidebar-title{{color:#FF5555;font-size:24px;font-weight:900;margin-bottom:32px;padding-bottom:20px;border-bottom:2px solid rgba(255,85,85,0.4);letter-spacing:1px}}
            .sidebar-section{{margin-bottom:32px}}
            .sidebar-label{{font-size:13px;color:#9ca3af;margin-bottom:12px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase}}
            .sidebar-input{{width:100%;padding:16px;background:rgba(26,16,37,0.7);border:2px solid rgba(255,85,85,0.3);color:#e5e7eb;border-radius:12px;font-size:15px;outline:none;backdrop-filter:blur(15px);transition:all 0.3s ease}}
            .sidebar-input:focus{{border-color:rgba(255,85,85,0.6);box-shadow:0 0 0 4px rgba(255,85,85,0.2);background:rgba(26,16,37,0.9)}}
            .sidebar-btn{{width:100%;padding:16px;background:linear-gradient(135deg, rgba(255,85,85,0.3), rgba(255,85,85,0.15));color:#FF5555;border:2px solid rgba(255,85,85,0.4);border-radius:12px;font-weight:900;cursor:pointer;margin-bottom:12px;backdrop-filter:blur(15px);transition:all 0.3s ease;font-size:15px;letter-spacing:0.5px}}
            .sidebar-btn:hover{{background:linear-gradient(135deg, rgba(255,85,85,0.5), rgba(255,85,85,0.25));border-color:rgba(255,85,85,0.7);transform:translateY(-2px);box-shadow:0 6px 20px rgba(255,85,85,0.3)}}
            .sidebar-ghost-btn{{width:100%;padding:16px;background:rgba(26,16,37,0.7);color:#e5e7eb;border:2px solid rgba(255,85,85,0.3);border-radius:12px;font-weight:900;cursor:pointer;margin-bottom:12px;backdrop-filter:blur(15px);transition:all 0.3s ease;font-size:15px;letter-spacing:0.5px}}
            .sidebar-ghost-btn:hover{{background:rgba(255,85,85,0.2);border-color:rgba(255,85,85,0.5);color:#FF5555;transform:translateX(-4px)}}
            .sidebar-module{{background:linear-gradient(135deg, rgba(26,16,37,0.9), rgba(26,16,37,0.7));border:2px solid rgba(255,85,85,0.3);border-radius:16px;padding:24px;margin-bottom:24px;backdrop-filter:blur(15px);box-shadow:0 8px 24px rgba(0,0,0,0.3)}}
            .avatar-module{{position:relative;overflow:hidden;margin-bottom:32px}}
            .avatar-module-bg{{width:100%;height:auto;display:block}}
            .avatar-module-content{{position:absolute;top:0;left:0;width:100%;height:100%;display:flex;align-items:center;gap:24px;padding:32px;background:transparent}}
            .modal{{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);backdrop-filter:blur(4px);z-index:9999}}
            .modal-content{{position:relative;background:rgba(26,16,37,0.9);border:1px solid rgba(255,85,85,0.3);border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,0.4),0 0 24px rgba(255,85,85,0.15);max-width:600px;margin:50px auto;padding:0;backdrop-filter:blur(20px)}}
            .modal-header{{padding:20px 24px;border-bottom:1px solid rgba(255,85,85,0.3);display:flex;justify-content:space-between;align-items:center}}
            .modal-title{{color:#FF5555;font-size:18px;font-weight:900;margin:0}}
            .modal-close{{background:transparent;border:none;color:#9ca3af;font-size:24px;cursor:pointer;padding:0;width:32px;height:32px;display:flex;align-items:center;justify-content:center;border-radius:8px}}
            .modal-close:hover{{background:rgba(255,85,85,0.2);color:#e5e7eb}}
            .modal-body{{padding:24px}}
            .avatar-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}}
            .avatar-option{{cursor:pointer;border:2px solid rgba(255,85,85,0.3);border-radius:12px;overflow:hidden;aspect-ratio:1;transition:all 0.3s ease;position:relative;backdrop-filter:blur(10px)}}
            .avatar-option:hover{{border-color:rgba(255,85,85,0.6)}}
            .avatar-option.selected{{border-color:rgba(255,85,85,0.8);box-shadow:0 0 0 3px rgba(255,85,85,0.2)}}
            .avatar-option img{{width:100%;height:100%;object-fit:cover;display:block}}
            .upload-section{{border-top:1px solid rgba(255,85,85,0.3);padding-top:20px}}
            .upload-btn{{display:flex;align-items:center;justify-content:center;gap:12px;margin-top:16px}}
            .hint{{color:#9ca3af;font-size:12px;margin-top:4px}}
        </style>
    </head>
    <body>
        <div class="user-info">
            <div class="username">{html_escape(display)}</div>
            <div class="avatar" onclick="openAvatarModal()" style="cursor:pointer;position:relative">
                <img src='{avatar}' alt='avatar' style="width:100%;height:100%;object-fit:cover">
            </div>
        </div>

        <div class="sidebar-toggle" onclick="toggleSidebar()">&lt;</div>

        <div class="sidebar" id="sidebar">
            <div class="sidebar-content">
                <div class="avatar-module">
                    <img src='/static/images/namecard/nc_taiko/name_card_short_0.png' alt='background' class='avatar-module-bg'>
                    <div class="avatar-module-content">
                        <div class="avatar" style="width:80px;height:80px">
                            <img src='{avatar}' alt='avatar' style="width:100%;height:100%;object-fit:cover">
                        </div>
                        <div>
                            <div style="color:#FF5555;font-size:18px;font-weight:900;margin-bottom:4px">{html_escape(display)}</div>
                            <div class="sidebar-label">{html_escape(username)}</div>
                        </div>
                    </div>
                </div>
                
                <div class="sidebar-module">
                    <div class="sidebar-label">修改昵称</div>
                    <form method="post" enctype="multipart/form-data">
                        <input type="text" name="nickname" value="{html_escape(nick)}" placeholder="设置昵称（最多30字符）" class="sidebar-input" style="margin-bottom:12px">
                        <button type="submit" class="sidebar-btn">保存昵称</button>
                    </form>
                </div>

                <div class="sidebar-module">
                    <div class="sidebar-label">修改头像</div>
                    <button class="sidebar-btn" onclick="openAvatarModal()">更换头像</button>
                </div>

                <div class="sidebar-module" style="margin-top:32px">
                    <a href="/" class="sidebar-ghost-btn">返回首页</a>
                    <a href="/logout" class="sidebar-ghost-btn">退出登录</a>
                </div>
            </div>
        </div>
        
        <!-- 头像选择弹窗 -->
        <div id="avatarModal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3 class="modal-title">选择头像</h3>
                    <button class="modal-close" onclick="closeAvatarModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="avatar-grid">
                        {"".join([f'''
                        <div class="avatar-option {'selected' if avatar == av else ''}" onclick="selectAvatar('{av}')" data-avatar="{av}">
                            <img src="{av}" alt="avatar_{i+1}">
                        </div>''' for i, av in enumerate(DEFAULT_AVATARS)])}
                    </div>
                    <div class="upload-section">
                        <div class="sidebar-label">或上传自定义头像</div>
                        <input type="file" id="avatarFile" accept=".png,.jpg,.jpeg,.gif,.webp" style="margin-top:8px;color:#cbd5e1">
                        <div class="upload-btn">
                            <button class="sidebar-btn" onclick="saveAvatar()">保存头像</button>
                            <button class="sidebar-ghost-btn" onclick="closeAvatarModal()">取消</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    <script>
        function toggleSidebar() {{
            const sidebar = document.getElementById('sidebar');
            const toggle = document.querySelector('.sidebar-toggle');
            sidebar.classList.toggle('active');
            toggle.classList.toggle('active');
        }}
        
        // 点击侧边栏外部关闭
        document.addEventListener('click', function(event) {{
            const sidebar = document.getElementById('sidebar');
            const toggle = document.querySelector('.sidebar-toggle');
            const userInfo = document.querySelector('.user-info');
            
            if (sidebar.classList.contains('active') && 
                !sidebar.contains(event.target) && 
                !toggle.contains(event.target) &&
                !userInfo.contains(event.target)) {{
                sidebar.classList.remove('active');
                toggle.classList.remove('active');
            }}
        }});
        
        let selectedAvatar = '{avatar}';
        
        function openAvatarModal() {{
            document.getElementById('avatarModal').style.display = 'block';
        }}
        
        function closeAvatarModal() {{
            document.getElementById('avatarModal').style.display = 'none';
        }}
        
        function selectAvatar(avatarUrl) {{
            document.querySelectorAll('.avatar-option').forEach(option => {{
                option.classList.remove('selected');
            }});
            event.currentTarget.classList.add('selected');
            selectedAvatar = avatarUrl;
        }}
        
        function saveAvatar() {{
            const fileInput = document.getElementById('avatarFile');
            
            if (fileInput.files && fileInput.files[0]) {{
                const formData = new FormData();
                formData.append('avatar', fileInput.files[0]);
                
                fetch('/update_avatar', {{
                    method: 'POST',
                    body: formData
                }}).then(() => {{
                    closeAvatarModal();
                    window.location.reload();
                }});
            }} else if (selectedAvatar && selectedAvatar !== '{avatar}') {{
                const formData = new FormData();
                formData.append('default_avatar', selectedAvatar);
                
                fetch('/update_avatar', {{
                    method: 'POST',
                    body: formData
                }}).then(() => {{
                    closeAvatarModal();
                    window.location.reload();
                }});
            }}
        }}
        
        window.onclick = function(event) {{
            const modal = document.getElementById('avatarModal');
            if (event.target === modal) {{
                closeAvatarModal();
            }}
        }}
    </script>
    </html>
    '''
    return html

@profile_bp.route('/update_avatar', methods=['POST'])
def update_avatar():
    if "user" not in session:
        return redirect("/login")
    username = session["user"]

    avatar_path = None
    
    # 检查是否选择了默认头像
    if "default_avatar" in request.form:
        default_avatar = request.form["default_avatar"]
        if default_avatar in DEFAULT_AVATARS:
            avatar_path = default_avatar
    
    # 检查是否上传了自定义头像
    elif "avatar" in request.files:
        f = request.files["avatar"]
        if f and f.filename:
            _, ext = os.path.splitext(f.filename.lower())
            if ext in ALLOWED_IMAGE_EXTS:
                ts = datetime.now().strftime("%Y%m%d%H%M%S%f")
                safe_user = "".join([c for c in username if c.isalnum() or c in ("_", "-")])[:30] or "u"
                filename = f"u_{safe_user}_{ts}{ext}"
                save_path = os.path.join(AVATAR_DIR, filename)
                f.save(save_path)
                avatar_path = f"/avatars/{filename}"

    if avatar_path:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("UPDATE users SET avatar=%s WHERE username=%s", (avatar_path, username))
        db.commit()
        db.close()
        clear_user_profile_cache(username)
    
    return "success"

@profile_bp.route('/user/<username>')
def user_public(username):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT username, nickname, avatar FROM users WHERE username=%s", (username,))
    info = cursor.fetchone()
    rooms = []
    try:
        cursor2 = db.cursor()
        cursor2.execute("SELECT id,name FROM rooms WHERE owner=%s", (username,))
        rooms = cursor2.fetchall()
    except:
        pass
    db.close()
    if not info:
        return "<h3>用户不存在</h3>"

    nick = (info.get("nickname") or "").strip()
    avatar = resolve_avatar_url(info.get("avatar"))
    display = nick if nick else info["username"]
    room_items = "".join([f"<li><a href='/room/{r[0]}'>{html_escape(r[1])}（ID {r[0]}）</a></li>" for r in rooms]) or "<li>暂无房间</li>"

    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>泰拉通讯 - 用户资料 - {html_escape(info["username"])}</title>
        <style>
            *{{margin:0;padding:0;box-sizing:border-box}}
            body{{background:#0a0a0f url('/static/images/namecard/nc_taiko/bg.png') center/cover no-repeat fixed;color:#e5e7eb;font-family:Segoe UI,微软雅黑;min-height:100vh;position:relative;overflow:hidden}}
            a{{text-decoration:none;color:#FF5555}}
            .user-info{{position:fixed;bottom:30px;right:30px;display:flex;align-items:center;gap:16px;z-index:10}}
            .avatar{{width:80px;height:80px;border-radius:12px;border:3px solid rgba(255,85,85,0.5);display:flex;align-items:center;justify-content:center;background:rgba(26,16,37,0.8);overflow:hidden;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,0.4),0 0 20px rgba(255,85,85,0.2);backdrop-filter:blur(10px)}}
            .avatar img{{width:100%;height:100%;object-fit:cover}}
            .username{{color:#FF5555;font-size:18px;font-weight:900;text-shadow:0 2px 8px rgba(0,0,0,0.5)}}
            .sidebar{{position:fixed;top:0;right:0;width:500px;height:100vh;background:transparent;border:none;transform:translateX(100%);transition:transform 0.4s cubic-bezier(0.4,0,0.2,1);z-index:1000;backdrop-filter:none;box-shadow:none}}
            .sidebar.active{{transform:translateX(0)}}
            .sidebar-toggle{{position:fixed;top:50%;right:20px;transform:translateY(-50%);width:50px;height:50px;background:rgba(255,85,85,0.3);color:#FF5555;border:1px solid rgba(255,85,85,0.5);border-radius:12px;cursor:pointer;font-size:24px;font-weight:900;display:flex;align-items:center;justify-content:center;z-index:999;backdrop-filter:blur(10px);transition:all 0.3s ease}}
            .sidebar-toggle:hover{{background:rgba(255,85,85,0.5);border-color:rgba(255,85,85,0.8)}}
            .sidebar-toggle.active{{transform:translateY(-50%) rotate(180deg)}}
            .sidebar-content{{padding:32px;overflow-y:auto;height:100vh}}
            .sidebar-section{{margin-bottom:32px}}
            .sidebar-label{{font-size:13px;color:#9ca3af;margin-bottom:12px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase}}
            .sidebar-module{{background:linear-gradient(135deg, rgba(26,16,37,0.9), rgba(26,16,37,0.7));border:2px solid rgba(255,85,85,0.3);border-radius:16px;padding:24px;margin-bottom:24px;backdrop-filter:blur(15px);box-shadow:0 8px 24px rgba(0,0,0,0.3)}}
            .avatar-module{{position:relative;overflow:hidden;margin-bottom:32px}}
            .avatar-module-bg{{width:100%;height:auto;display:block}}
            .avatar-module-content{{position:absolute;top:0;left:0;width:100%;height:100%;display:flex;align-items:center;gap:24px;padding:32px;background:transparent}}
            .sidebar-ghost-btn{{width:100%;padding:16px;background:rgba(26,16,37,0.7);color:#e5e7eb;border:2px solid rgba(255,85,85,0.3);border-radius:12px;font-weight:900;cursor:pointer;margin-bottom:12px;backdrop-filter:blur(15px);transition:all 0.3s ease;font-size:15px;letter-spacing:0.5px}}
            .sidebar-ghost-btn:hover{{background:rgba(255,85,85,0.2);border-color:rgba(255,85,85,0.5);color:#FF5555;transform:translateX(-4px)}}
            .info-value{{color:#e5e7eb;font-size:15px;margin-bottom:8px}}
            .info-label{{color:#FF5555;font-size:13px;font-weight:700;margin-bottom:4px}}
            ul{{margin-top:8px;padding-left:20px}}
            li{{margin-bottom:8px;color:#e5e7eb}}
        </style>
    </head>
    <body>
        <div class="user-info">
            <div class="avatar">{
                f"<img src='{avatar}' alt='avatar'>" if avatar else f"<div style='font-size:28px;color:#FF5555;font-weight:900'>{html_escape(display)[:1].upper()}</div>"
            }</div>
            <div class="username">{html_escape(display)}</div>
        </div>

        <div class="sidebar-toggle" onclick="toggleSidebar()">&lt;</div>

        <div class="sidebar" id="sidebar">
            <div class="sidebar-content">
                <div class="avatar-module">
                    <img src='/static/images/namecard/nc_taiko/name_card_short_0.png' alt='background' class='avatar-module-bg'>
                    <div class="avatar-module-content">
                        <div class="avatar" style="width:80px;height:80px">{
                            f"<img src='{avatar}' alt='avatar' style='width:100%;height:100%;object-fit:cover'>" if avatar else f"<div style='font-size:28px;color:#FF5555;font-weight:900'>{html_escape(display)[:1].upper()}</div>"
                        }</div>
                        <div>
                            <div style="color:#FF5555;font-size:18px;font-weight:900;margin-bottom:4px">{html_escape(display)}</div>
                            <div class="sidebar-label">{html_escape(info["username"])}</div>
                        </div>
                    </div>
                </div>

                <div class="sidebar-module">
                    <div class="sidebar-label">用户信息</div>
                    <div class="info-label">昵称</div>
                    <div class="info-value">{html_escape(display)}</div>
                    <div class="info-label">账号</div>
                    <div class="info-value">{html_escape(info["username"])}</div>
                </div>

                <div class="sidebar-module">
                    <div class="sidebar-label">TA 的房间</div>
                    <ul>{room_items}</ul>
                </div>

                <div class="sidebar-module" style="margin-top:32px">
                    <a href="javascript:history.back()" class="sidebar-ghost-btn">返回</a>
                    <a href="/" class="sidebar-ghost-btn">首页</a>
                </div>
            </div>
        </div>

        <script>
            function toggleSidebar() {{
                const sidebar = document.getElementById('sidebar');
                const toggle = document.querySelector('.sidebar-toggle');
                sidebar.classList.toggle('active');
                toggle.classList.toggle('active');
            }}

            document.addEventListener('click', function(e) {{
                const sidebar = document.getElementById('sidebar');
                const toggle = document.querySelector('.sidebar-toggle');
                const userInfo = document.querySelector('.user-info');
                
                if (!sidebar.contains(e.target) && !toggle.contains(e.target) && !userInfo.contains(e.target)) {{
                    sidebar.classList.remove('active');
                    toggle.classList.remove('active');
                }}
            }});

            document.querySelector('.user-info').addEventListener('click', function() {{
                toggleSidebar();
            }});
        </script>
    </body>
    </html>
    '''
    return html
