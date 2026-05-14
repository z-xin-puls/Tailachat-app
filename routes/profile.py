# 个人中心路由
from flask import Blueprint, request, redirect, render_template_string, session, send_from_directory, jsonify

# 导入自定义异常
from utils.exceptions import AppError, ValidationError, AuthenticationError, AuthorizationError, DatabaseError

# 导入密码工具
from utils.password import hash_password, verify_password
from models.database import get_db_connection
from models.user import get_user_profiles, clear_user_profile_cache, resolve_avatar_url
from utils.helpers import html_escape
from config import DEFAULT_AVATARS, ALLOWED_IMAGE_EXTS, AVATAR_DIR
import os
from datetime import datetime
from PIL import Image
import io

profile_bp = Blueprint('profile', __name__)

# 头像配置
MAX_AVATAR_SIZE = 500  # 最大尺寸500x500
AVATAR_QUALITY = 85    # JPEG质量85%

def compress_avatar(image_file, skip_compression=False):
    """压缩头像图片
    
    Args:
        image_file: 图片文件对象
        skip_compression: 是否跳过压缩（前端已裁剪的图片）
    """
    try:
        img = Image.open(image_file)
        
        # 如果前端已经裁剪过，直接保存为JPEG
        if skip_compression:
            output = io.BytesIO()
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.save(output, format='JPEG', quality=AVATAR_QUALITY, optimize=True)
            output.seek(0)
            return output
        
        # 转换为RGB（处理RGBA图片）
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 计算缩放比例
        width, height = img.size
        if width > MAX_AVATAR_SIZE or height > MAX_AVATAR_SIZE:
            ratio = min(MAX_AVATAR_SIZE / width, MAX_AVATAR_SIZE / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 保存到内存
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=AVATAR_QUALITY, optimize=True)
        output.seek(0)
        
        return output
    except Exception as e:
        print(f"图片压缩失败: {e}")
        raise

def delete_old_avatar(username, new_avatar_path=None):
    """删除用户的旧头像文件
    
    Args:
        username: 用户名
        new_avatar_path: 新头像路径（用于避免删除与旧头像相同的文件）
    """
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT avatar FROM users WHERE username=%s", (username,))
        result = cursor.fetchone()
        db.close()
        
        if result and result[0]:
            old_avatar = result[0]
            # 只删除自定义上传的头像（以/avatars/开头的）
            if old_avatar.startswith('/avatars/'):
                # 避免删除新上传的文件（如果新旧路径相同）
                if new_avatar_path and old_avatar == new_avatar_path:
                    return
                    
                filename = old_avatar[len('/avatars/'):]
                old_path = os.path.join(AVATAR_DIR, filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
                    print(f"已删除旧头像: {filename}")
    except Exception as e:
        print(f"删除旧头像失败: {e}")

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
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.css">
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
            .modal-content{{position:relative;background:rgba(26,16,37,0.9);border:1px solid rgba(255,85,85,0.3);border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,0.4),0 0 24px rgba(255,85,85,0.15);max-width:600px;max-height:90vh;margin:5vh auto;padding:0;backdrop-filter:blur(20px);overflow-y:auto}}
            .modal-header{{padding:16px 20px;border-bottom:1px solid rgba(255,85,85,0.3);display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;background:rgba(26,16,37,0.95);z-index:10}}
            .modal-title{{color:#FF5555;font-size:16px;font-weight:900;margin:0}}
            .modal-close{{background:transparent;border:none;color:#9ca3af;font-size:24px;cursor:pointer;padding:0;width:28px;height:28px;display:flex;align-items:center;justify-content:center;border-radius:8px}}
            .modal-close:hover{{background:rgba(255,85,85,0.2);color:#e5e7eb}}
            .modal-body{{padding:16px 20px}}
            .avatar-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}}
            .avatar-option{{cursor:pointer;border:2px solid rgba(255,85,85,0.3);border-radius:10px;overflow:hidden;aspect-ratio:1;transition:all 0.3s ease;position:relative;backdrop-filter:blur(10px)}}
            .avatar-option:hover{{border-color:rgba(255,85,85,0.6)}}
            .avatar-option.selected{{border-color:rgba(255,85,85,0.8);box-shadow:0 0 0 3px rgba(255,85,85,0.2)}}
            .avatar-option img{{width:100%;height:100%;object-fit:cover;display:block}}
            .upload-section{{border-top:1px solid rgba(255,85,85,0.3);padding-top:16px}}
            .upload-btn{{display:flex;align-items:center;justify-content:center;gap:8px;margin-top:12px;flex-wrap:wrap}}
            .hint{{color:#9ca3af;font-size:11px;margin-top:4px}}
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
                    <div class="sidebar-label">修改密码</div>
                    <form method="post" action="/change_password">
                        <input type="password" name="old_password" placeholder="当前密码" class="sidebar-input" style="margin-bottom:12px">
                        <input type="password" name="new_password" placeholder="新密码" class="sidebar-input" style="margin-bottom:12px">
                        <input type="password" name="confirm_password" placeholder="确认新密码" class="sidebar-input" style="margin-bottom:12px">
                        <button type="submit" class="sidebar-btn">修改密码</button>
                    </form>
                </div>

                <div class="sidebar-module">
                    <div class="sidebar-label">修改头像</div>
                    <button class="sidebar-btn" onclick="openAvatarModal()">更换头像</button>
                </div>

                <div class="sidebar-module" style="margin-top:32px">
                    <a href="/" class="sidebar-ghost-btn">返回首页</a>
                    <a href="/logout" class="sidebar-ghost-btn">退出登录</a>
                    <button class="sidebar-ghost-btn" onclick="openDeleteModal()" style="background:rgba(239,68,68,0.2);border-color:rgba(239,68,68,0.4);color:#ef4444;margin-top:24px;">删除账号</button>
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
                    <div class="upload-btn" style="margin-top:16px;">
                        <button class="sidebar-btn" onclick="saveDefaultAvatar()">保存头像</button>
                        <button class="sidebar-ghost-btn" onclick="closeAvatarModal()">取消</button>
                    </div>
                    <div class="upload-section" style="margin-top:16px;">
                        <div class="sidebar-label">或上传自定义头像</div>
                        <button class="sidebar-btn" onclick="openCustomAvatarModal()" style="margin-top:8px;">上传自定义头像</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 自定义头像上传弹窗 -->
        <div id="customAvatarModal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3 class="modal-title">上传自定义头像</h3>
                    <button class="modal-close" onclick="closeCustomAvatarModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <input type="file" id="customAvatarFile" accept=".png,.jpg,.jpeg,.gif,.webp" style="color:#cbd5e1" onchange="previewCustomAvatar(this)">
                    
                    <div id="customPreviewContainer" style="display:none;margin-top:16px;">
                        <div class="sidebar-label">预览与裁剪</div>
                        <div style="position:relative;width:100%;max-width:400px;height:300px;background:rgba(0,0,0,0.3);border-radius:10px;overflow:hidden;margin-bottom:12px;">
                            <img id="customAvatarPreview" style="max-width:100%;display:block;">
                        </div>
                        <div class="upload-btn">
                            <button class="sidebar-btn" onclick="saveCustomAvatar()" style="flex:1">保存头像</button>
                            <button class="sidebar-ghost-btn" onclick="resetCustomAvatar()" style="flex:1">重新选择</button>
                            <button class="sidebar-ghost-btn" onclick="closeCustomAvatarModal()" style="flex:1">取消</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 删除账号确认弹窗 -->
        <div id="deleteModal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3 class="modal-title">删除账号</h3>
                    <button class="modal-close" onclick="closeDeleteModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <div style="color:#ef4444;font-weight:700;margin-bottom:16px;">⚠️ 危险操作</div>
                    <p style="margin-bottom:16px;color:#9ca3af;">删除账号后将无法恢复，所有数据将被永久删除：</p>
                    <ul style="color:#9ca3af;margin-left:20px;margin-bottom:20px;">
                        <li>个人资料和头像</li>
                        <li>创建的房间</li>
                        <li>聊天记录</li>
                        <li>所有相关数据</li>
                    </ul>
                    
                    <div class="sidebar-label">确认密码</div>
                    <input type="password" id="deletePassword" placeholder="请输入当前密码确认删除" class="sidebar-input" style="margin-bottom:16px;">
                    
                    <div style="display:flex;gap:12px;">
                        <button class="sidebar-btn" onclick="confirmDeleteAccount()" style="background:rgba(239,68,68,0.3);border-color:rgba(239,68,68,0.5);color:#ef4444;flex:1;">确认删除</button>
                        <button class="sidebar-ghost-btn" onclick="closeDeleteModal()" style="flex:1;">取消</button>
                    </div>
                </div>
            </div>
        </div>
    </body>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.js"></script>
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
        let customCropper = null;
        
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
        
        function saveDefaultAvatar() {{
            if (selectedAvatar && selectedAvatar !== '{avatar}') {{
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
        
        function openCustomAvatarModal() {{
            document.getElementById('customAvatarModal').style.display = 'block';
            closeAvatarModal();
        }}
        
        function closeCustomAvatarModal() {{
            document.getElementById('customAvatarModal').style.display = 'none';
            if (customCropper) {{
                customCropper.destroy();
                customCropper = null;
            }}
        }}
        
        function previewCustomAvatar(input) {{
            if (input.files && input.files[0]) {{
                const reader = new FileReader();
                reader.onload = function(e) {{
                    const preview = document.getElementById('customAvatarPreview');
                    preview.src = e.target.result;
                    document.getElementById('customPreviewContainer').style.display = 'block';
                    input.style.display = 'none';
                    
                    // 初始化裁剪器
                    if (customCropper) {{
                        customCropper.destroy();
                    }}
                    customCropper = new Cropper(preview, {{
                        aspectRatio: 1,
                        viewMode: 1,
                        dragMode: 'move',
                        autoCropArea: 0.8,
                        restore: false,
                        guides: true,
                        center: true,
                        highlight: true,
                        cropBoxMovable: true,
                        cropBoxResizable: true,
                        toggleDragModeOnDblclick: false
                    }});
                }};
                reader.readAsDataURL(input.files[0]);
            }}
        }}
        
        function resetCustomAvatar() {{
            document.getElementById('customAvatarFile').value = '';
            document.getElementById('customPreviewContainer').style.display = 'none';
            document.getElementById('customAvatarFile').style.display = 'block';
            if (customCropper) {{
                customCropper.destroy();
                customCropper = null;
            }}
        }}
        
        function saveCustomAvatar() {{
            if (customCropper) {{
                // 获取裁剪后的画布
                const canvas = customCropper.getCroppedCanvas({{
                    width: 500,
                    height: 500,
                    imageSmoothingEnabled: true,
                    imageSmoothingQuality: 'high'
                }});
                
                // 转换为Blob
                canvas.toBlob(function(blob) {{
                    const formData = new FormData();
                    formData.append('avatar', blob, 'avatar.jpg');
                    formData.append('cropped', 'true');  // 标记为前端已裁剪
                    
                    fetch('/update_avatar', {{
                        method: 'POST',
                        body: formData
                    }}).then(() => {{
                        closeCustomAvatarModal();
                        window.location.reload();
                    }});
                }}, 'image/jpeg', 0.85);
            }}
        }}
        
        // 删除账号相关函数
        function openDeleteModal() {{
            document.getElementById('deleteModal').style.display = 'block';
            document.getElementById('deletePassword').value = '';
        }}
        
        function closeDeleteModal() {{
            document.getElementById('deleteModal').style.display = 'none';
            document.getElementById('deletePassword').value = '';
        }}
        
        async function confirmDeleteAccount() {{
            const password = document.getElementById('deletePassword').value;
            
            if (!password) {{
                alert('请输入密码确认删除操作');
                return;
            }}
            
            if (!confirm('再次确认：删除账号后无法恢复，确定要继续吗？')) {{
                return;
            }}
            
            try {{
                const response = await fetch('/delete_account', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{ password: password }})
                }});
                
                if (!response.ok) {{
                    throw new Error(`HTTP error! status: ${{response.status}}`);
                }}
                
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {{
                    throw new Error('服务器返回了非JSON响应');
                }}
                
                const data = await response.json();
                
                if (data.success) {{
                    alert('账号已成功删除');
                    window.location.href = '/'; // 跳转到首页
                }} else {{
                    alert(data.error || '删除失败');
                }}
            }} catch (error) {{
                console.error('删除账号错误:', error);
                alert('删除失败: ' + error.message);
            }}
        }}
        
        window.onclick = function(event) {{
            const modal = document.getElementById('avatarModal');
            if (event.target === modal) {{
                closeAvatarModal();
            }}
            const customModal = document.getElementById('customAvatarModal');
            if (event.target === customModal) {{
                closeCustomAvatarModal();
            }}
            const deleteModal = document.getElementById('deleteModal');
            if (event.target === deleteModal) {{
                closeDeleteModal();
            }}
        }}
    </script>
    </html>
    '''
    return html

@profile_bp.route('/change_password', methods=['POST'])
def change_password():
    if "user" not in session:
        return redirect("/login")
    username = session["user"]

    old_password = request.form.get("old_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    # 验证输入
    if not old_password or not new_password or not confirm_password:
        return "<h3>所有字段都必须填写</h3>"

    if new_password != confirm_password:
        return "<h3>两次输入的新密码不一致</h3>"

    # 验证密码格式
    from utils.validators import validate_password
    error = validate_password(new_password)
    if error:
        raise ValidationError(error)

    db = get_db_connection()
    cursor = db.cursor()

    try:
        # 验证旧密码
        cursor.execute("SELECT password FROM users WHERE username=%s", (username,))
        result = cursor.fetchone()

        if not result:
            raise AuthenticationError("用户不存在")

        stored_password = result[0]
        if not verify_password(old_password, stored_password):
            raise AuthenticationError("当前密码错误")

        # 更新新密码（加密后存储）
        hashed_new_password = hash_password(new_password)
        cursor.execute("UPDATE users SET password=%s WHERE username=%s", (hashed_new_password, username))
        db.commit()
        db.close()

        return "<h3>密码修改成功，请重新登录</h3><script>setTimeout(function(){window.location='/logout'}, 2000);</script>"

    except Exception as e:
        db.rollback()
        db.close()
        print(f"修改密码失败: {e}")
        raise DatabaseError("修改密码失败")

@profile_bp.route('/update_avatar', methods=['POST'])
def update_avatar():
    if "user" not in session:
        return redirect("/login")
    username = session["user"]

    avatar_path = None
    old_avatar_deleted = False
    
    # 检查是否选择了默认头像
    if "default_avatar" in request.form:
        default_avatar = request.form["default_avatar"]
        if default_avatar in DEFAULT_AVATARS:
            # 删除旧的自定义头像
            delete_old_avatar(username, new_avatar_path=default_avatar)
            avatar_path = default_avatar
    
    # 检查是否上传了自定义头像
    elif "avatar" in request.files:
        f = request.files["avatar"]
        if f and f.filename:
            _, ext = os.path.splitext(f.filename.lower())
            if ext in ALLOWED_IMAGE_EXTS:
                try:
                    # 检查是否为前端裁剪的图片
                    is_cropped = request.form.get("cropped") == "true"
                    
                    # 压缩图片（前端裁剪的跳过压缩）
                    compressed = compress_avatar(f, skip_compression=is_cropped)
                    
                    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")
                    safe_user = "".join([c for c in username if c.isalnum() or c in ("_", "-")])[:30] or "u"
                    filename = f"u_{safe_user}_{ts}.jpg"  # 统一保存为JPEG
                    save_path = os.path.join(AVATAR_DIR, filename)
                    
                    # 保存压缩后的图片
                    with open(save_path, 'wb') as out_file:
                        out_file.write(compressed.getvalue())
                    
                    avatar_path = f"/avatars/{filename}"
                except Exception as e:
                    print(f"头像处理失败: {e}")
                    raise DatabaseError("头像处理失败")

    if avatar_path:
        try:
            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute("UPDATE users SET avatar=%s WHERE username=%s", (avatar_path, username))
            db.commit()
            db.close()
            clear_user_profile_cache(username)
            
            # 更新成功后删除旧头像
            delete_old_avatar(username, new_avatar_path=avatar_path)
            old_avatar_deleted = True
        except Exception as e:
            print(f"更新头像失败: {e}")
            # 如果更新失败且已保存新文件，删除新文件
            if avatar_path.startswith('/avatars/'):
                filename = avatar_path[len('/avatars/'):]
                new_path = os.path.join(AVATAR_DIR, filename)
                if os.path.exists(new_path):
                    os.remove(new_path)
            raise DatabaseError("更新头像失败")
    
    return "success"

@profile_bp.route('/delete_account', methods=['POST'])
def delete_account():
    """用户自我删除账号 - 使用新的错误处理机制"""
    
    # 检查登录状态
    if "user" not in session:
        raise AuthenticationError("请先登录")
    
    username = session["user"]
    
    # 获取请求数据
    data = request.get_json()
    if not data:
        raise ValidationError("请求数据格式错误")
        
    password = data.get('password', '')
    if not password:
        raise ValidationError("请输入密码")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 验证用户存在和密码
        cursor.execute("SELECT password, role FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        
        if not result:
            raise AuthenticationError("用户不存在")
        
        stored_password, user_role = result
        
        if not verify_password(password, stored_password):
            raise AuthenticationError("密码错误")
        
        # 检查管理员权限
        if user_role == 'admin':
            raise AuthorizationError("管理员账号不能删除")
        
        # 删除用户相关数据
        cursor.execute("DELETE FROM rooms WHERE owner = %s", (username,))
        cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        
        conn.commit()
        conn.close()
        
        # 清除session
        session.pop('user', None)
        
        return jsonify({'success': True, 'message': '账号删除成功'})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"删除用户数据失败: {e}")
        raise DatabaseError("删除失败，请稍后重试")

@profile_bp.route('/user/<username>')
def user_public(username):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT username, nickname, avatar FROM users WHERE username=%s", (username,))
    info = cursor.fetchone()
    rooms = []
    try:
        cursor.execute("SELECT id, name FROM rooms WHERE owner=%s", (username,))
        rooms = cursor.fetchall()
    except Exception as e:
        print(f"获取用户房间失败: {e}")
    db.close()
    if not info:
        return "<h3>用户不存在</h3>"

    nick = (info.get("nickname") or "").strip()
    avatar = resolve_avatar_url(info.get("avatar"))
    display = nick if nick else info["username"]
    room_items = "".join([f"<li><a href='/room/{r['id']}'>{html_escape(r['name'])}（ID {r['id']}）</a></li>" for r in rooms]) or "<li>暂无房间</li>"

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
