# 小T语音应用 - 重构版本
from flask import Flask, render_template_string, request, redirect, session, send_from_directory
import mysql.connector
import sys
import subprocess
import os
import requests
import socket
import json
import threading
from datetime import datetime
import time

# 导入配置
from config import SECRET_KEY, DB_CONFIG, PROFILE_CACHE_TTL_SECONDS

# 导入数据模型
from models.database import get_db_connection, ensure_user_profile_columns, ensure_room_location_columns
from models.user import get_user_profiles, clear_user_profile_cache, resolve_avatar_url, format_user_label
from models.room import get_room_by_id, create_room

# 导入验证函数
from utils.validators import validate_room_name

# 导入路由蓝图
from routes.auth import auth_bp
from routes.main import main_bp
from routes.profile import profile_bp

# 创建Flask应用
app = Flask(__name__)
app.secret_key = SECRET_KEY

# 全局变量
voice_processes = {}
room_users = {}
chat_rooms = {}
chat_lock = threading.Lock()

# 注册蓝图
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(profile_bp)

# 初始化数据库结构
@app.before_request
def _init_profile_schema():
    ensure_user_profile_columns()
    ensure_room_location_columns()

# 剩余的路由（房间相关、API等）
@app.route('/room/<id>')
def room(id):
    if "user" not in session:
        return redirect("/login")

    user = session['user']
    if id not in room_users:
        room_users[id] = set()
    room_users[id].add(user)

    voice_users = []
    speaking_user = None
    try:
        response = requests.get(f'http://127.0.0.1:5001/api/room-users/{id}', timeout=2)
        if response.status_code == 200:
            data = response.json()
            voice_users = data.get('users', [])
            speaking_user = data.get('speaking')
    except:
        pass

    web_users = room_users.get(id, set())
    all_users = web_users | set(voice_users)
    count = len(all_users)

    profiles = get_user_profiles(all_users)
    self_prof = profiles.get(user) or get_user_profiles([user]).get(user) or {}
    self_display = (self_prof.get("nickname") or user)

    member_items = ""
    for u in sorted(all_users):
        safe_u = u.replace("'", "").replace('"', "")
        label = format_user_label(u, profiles.get(u))
        info_link = f"<a class='user-info' href='/user/{safe_u}' onclick=\"event.stopPropagation();\">资料</a>"
        if u == speaking_user:
            member_items += f"<li class='user-item speaking' onclick=\"openVolumePanel('{safe_u}')\"><div class='user-main'><span class='badge badge-green'>说话</span>{label}</div><div class='user-meta'>🎤 {info_link}</div></li>"
        elif u in voice_users:
            member_items += f"<li class='user-item voice' onclick=\"openVolumePanel('{safe_u}')\"><div class='user-main'><span class='badge badge-teal'>语音</span>{label}</div><div class='user-meta'>✅ {info_link}</div></li>"
        else:
            member_items += f"<li class='user-item online' onclick=\"openVolumePanel('{safe_u}')\"><div class='user-main'><span class='badge badge-gray'>在线</span>{label}</div><div class='user-meta'>• {info_link}</div></li>"

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>小T语音 - 房间 {id}</title>
        <style>
            *{{margin:0;padding:0;box-sizing:border-box}}
            body{{background:#111827;color:#fff;font-family:Segoe UI,微软雅黑;min-height:100vh}}
            a{{text-decoration:none;color:inherit}}
            #particleCanvas{{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9999;opacity:0.8}}
            .container{{max-width:1200px;margin:0 auto;padding:24px}}
            .topbar{{display:flex;gap:14px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap}}
            .brand{{display:flex;flex-direction:column;gap:4px}}
            .brand-title{{color:#2dd4bf;font-size:26px;font-weight:900;letter-spacing:.5px}}
            .brand-sub{{color:#9ca3af;font-size:13px}}
            .meta{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
            .pill{{display:inline-flex;gap:8px;align-items:center;padding:7px 10px;border-radius:999px;background:#1f2937;border:1px solid #111827;color:#cbd5e1;font-size:12px}}
            .pill strong{{color:#fff}}
            .pill-green{{border-color:#10b98155}}
            .actions{{display:flex;gap:10px;flex-wrap:wrap}}
            .btn{{display:inline-flex;align-items:center;justify-content:center;padding:10px 14px;border-radius:10px;border:1px solid transparent;font-weight:900;cursor:pointer;user-select:none;white-space:nowrap}}
            .btn-green{{background:#10b981;color:#fff}}
            .btn-red{{background:#ef4444;color:#fff}}
            .btn-ghost{{background:transparent;color:#e5e7eb;border-color:#374151}}
            .btn:hover{{filter:brightness(1.03)}}
            .grid{{display:none}} /* 隐藏原来的网格布局 */
            .sidebar-left, .sidebar-right{{position:fixed;top:50%;transform:translateY(-50%);background:rgba(31,41,55,0.9);border:1px solid rgba(17,24,39,0.6);border-radius:16px;z-index:10;transition:all 0.3s ease;backdrop-filter:blur(10px);box-shadow:0 8px 32px rgba(0,0,0,0.3)}}
            .sidebar-left{{left:20px;width:280px}}
            .sidebar-right{{right:20px;width:320px}}
            .sidebar-collapsed{{width:50px;height:50px}}
            .sidebar-expanded{{width:auto;max-height:600px;overflow-y:auto}}
            .sidebar-toggle{{width:100%;height:50px;background:rgba(45,212,191,0.2);border:none;border-radius:16px 16px 0 0;cursor:pointer;font-size:18px;font-weight:900;display:flex;align-items:center;justify-content:center;transition:all 0.3s ease;color:#2dd4bf}}
            .sidebar-toggle:hover{{background:rgba(45,212,191,0.3);transform:scale(1.02)}}
            .sidebar-content{{padding:16px;display:none}}
            .sidebar-expanded .sidebar-content{{display:block}}
            .sidebar-header{{margin-bottom:16px}}
            .sidebar-title{{color:#2dd4bf;font-size:16px;font-weight:900;margin-bottom:4px}}
            .sidebar-hint{{color:#9ca3af;font-size:11px}}
            .sidebar-left .sidebar-content{{max-height:400px;overflow-y:auto}}
            .sidebar-right .sidebar-content{{max-height:500px;overflow-y:auto}}
            .card{{background:#1f2937;border:1px solid #111827;border-radius:16px;box-shadow:0 0 18px #0004}}
            .card-head{{padding:16px 16px 0}}
            .card-title{{font-size:16px;font-weight:900}}
            .hint{{color:#9ca3af;font-size:12px;margin-top:6px}}
            .card-body{{padding:14px 16px 16px}}
            .chat-wrap{{margin-top:14px}}
            .chat-box{{height:280px;overflow:auto;padding:12px;border-radius:14px;background:#111827;border:1px solid #374151}}
            .chat-line{{display:flex;gap:10px;align-items:flex-start;margin-bottom:10px}}
            .chat-time{{color:#6b7280;font-size:12px;min-width:70px}}
            .chat-user{{color:#2dd4bf;font-weight:900;min-width:80px;max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
            .chat-text{{color:#e5e7eb;white-space:pre-wrap;word-break:break-word;flex:1}}
            .chat-row{{display:flex;gap:10px;margin-top:10px}}
            .chat-input{{flex:1;padding:12px 14px;background:#111827;border:1px solid #374151;color:#fff;border-radius:12px;font-size:14px;outline:none}}
            .chat-input:focus{{border-color:#2dd4bf;box-shadow:0 0 0 3px #2dd4bf22}}
            .chat-send{{padding:12px 16px;border-radius:12px;background:#2dd4bf;color:#111;font-weight:900;border:none;cursor:pointer}}
            .chat-send:hover{{filter:brightness(1.03)}}
            .user-list{{list-style:none;display:flex;flex-direction:column;gap:8px}}
            .user-item{{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 12px;border-radius:12px;background:#111827;border:1px solid #374151;cursor:pointer;transition:transform .08s ease, border-color .08s ease}}
            .user-item:hover{{transform:translateY(-1px);border-color:#2dd4bf55}}
            .user-main{{display:flex;gap:10px;align-items:center;min-width:0}}
            .user-name{{font-weight:900;color:#fff;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
            .user-sub{{color:#9ca3af;font-size:12px;margin-left:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
            .user-meta{{color:#9ca3af}}
            .user-info{{margin-left:10px;color:#93c5fd;border:1px solid #374151;padding:2px 8px;border-radius:10px;font-size:12px}}
            .user-info:hover{{filter:brightness(1.1)}}
            .badge{{display:inline-flex;align-items:center;justify-content:center;padding:4px 8px;border-radius:999px;font-size:12px;font-weight:900;border:1px solid transparent}}
            .badge-green{{background:#10b98122;color:#10b981;border-color:#10b98155}}
            .badge-teal{{background:#2dd4bf22;color:#2dd4bf;border-color:#2dd4bf55}}
            .badge-gray{{background:#37415155;color:#cbd5e1;border-color:#374151}}
            .panel{{display:flex;flex-direction:column;gap:10px}}
            .legend{{display:flex;flex-direction:column;gap:10px;margin-top:4px}}
            .legend-item{{display:flex;gap:10px;align-items:center;color:#cbd5e1;font-size:13px}}
            .dot{{width:10px;height:10px;border-radius:99px}}
            .dot-green{{background:#10b981}}
            .dot-teal{{background:#2dd4bf}}
            .dot-gray{{background:#9ca3af}}
            .backdrop{{display:none;position:fixed;inset:0;background:#0008;backdrop-filter:blur(4px);padding:18px;z-index:9999}}
            .modal{{max-width:420px;margin:8vh auto 0;background:#1f2937;border:1px solid #111827;border-radius:16px;box-shadow:0 0 30px #000a;overflow:hidden}}
            .modal-head{{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;border-bottom:1px solid #111827}}
            .modal-title{{color:#2dd4bf;font-weight:900}}
            .icon-btn{{background:transparent;border:1px solid #374151;color:#e5e7eb;width:34px;height:34px;border-radius:10px;cursor:pointer;font-size:18px;line-height:0}}
            .icon-btn:hover{{filter:brightness(1.05)}}
            .modal-body{{padding:14px 16px 16px}}
            .mono{{font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace}}
            .row{{display:flex;align-items:center;justify-content:space-between;gap:10px}}
            .slider{{width:100%;margin-top:8px}}
            .section{{margin-top:14px}}
            .section:first-child{{margin-top:0}}
            input[type="range"]{{accent-color:#2dd4bf}}
            .disabled{{opacity:.55;pointer-events:none}}
        </style>
    </head>
    <body>
        <canvas id="particleCanvas"></canvas>
        <div class="container">
            <div class="topbar">
                <div class="brand">
                    <div class="brand-title">🎧 小T语音</div>
                    <div class="brand-sub">点击成员可独立调节音量（不影响语音传输）</div>
                </div>
                <div class="meta">
                    <div class="pill">房间 <strong class="mono">{id}</strong></div>
                    <div class="pill">当前用户 <strong class="mono">{self_display}</strong></div>
                    <div class="pill pill-green">在线 <strong id="user-count">{count}</strong></div>
                </div>
                <div class="actions">
                    <button class="btn btn-green" onclick="startVoiceClient()">启动语音</button>
                    <button class="btn btn-red" onclick="stopVoiceClient()">关闭语音</button>
                    <a class="btn btn-ghost" href="/profile">个人中心</a>
                    <a class="btn btn-ghost" href="/leave-room/{id}">退出房间</a>
                    <a class="btn btn-ghost" href="/">返回列表</a>
                </div>
            </div>

            <!-- 左侧边栏 - 房间成员 -->
            <div class="sidebar-left" id="sidebarLeft">
                <div class="sidebar-toggle" id="sidebarLeftToggle">
                    <span class="toggle-icon">👥</span>
                </div>
                <div class="sidebar-content">
                    <div class="sidebar-header">
                        <div class="sidebar-title">房间成员</div>
                        <div class="sidebar-hint">点击调节音量</div>
                    </div>
                    <ul id="user-list" class="user-list">{member_items}</ul>
                </div>
            </div>

            <!-- 右侧边栏 - 文字聊天 -->
            <div class="sidebar-right" id="sidebarRight">
                <div class="sidebar-toggle" id="sidebarRightToggle">
                    <span class="toggle-icon">💬</span>
                </div>
                <div class="sidebar-content">
                    <div class="sidebar-header">
                        <div class="sidebar-title">文字聊天</div>
                        <div class="sidebar-hint">不影响语音</div>
                    </div>
                    <div id="chat-box" class="chat-box"></div>
                    <div class="chat-row">
                        <input id="chat-input" class="chat-input" placeholder="输入消息，回车发送">
                        <button class="chat-send" onclick="sendChat()">发送</button>
                    </div>
                </div>
            </div>
        </div>

        <div id="vol-backdrop" class="backdrop" onclick="closeVolumePanel()">
            <div id="vol-panel" class="modal" onclick="event.stopPropagation()">
                <div class="modal-head">
                    <div class="modal-title">音量设置</div>
                    <button class="icon-btn" onclick="closeVolumePanel()">×</button>
                </div>
                <div class="modal-body">
                    <div class="row" style="margin-bottom:10px">
                        <div style="color:#cbd5e1">目标用户</div>
                        <div id="vol-target" class="mono" style="color:#10b981;font-weight:900"></div>
                    </div>

                    <div class="section">
                        <div class="row">
                            <div>🎙️ 麦克风音量</div>
                            <div id="mic-val" style="color:#2dd4bf;font-weight:900">100%</div>
                        </div>
                        <input id="mic-slider" class="slider" type="range" min="0" max="200" value="100">
                    </div>

                    <div class="section">
                        <div class="row">
                            <div>🔊 听到TA的音量</div>
                            <div id="play-val" style="color:#2dd4bf;font-weight:900">100%</div>
                        </div>
                        <input id="play-slider" class="slider" type="range" min="0" max="200" value="100">
                        <div id="play-hint" class="hint" style="margin-top:8px"></div>
                    </div>
                </div>
            </div>
        </div>

    <script>
        let currentTarget = '';
        const selfUser = '{user}';

        setInterval(() => {{
            fetch('/room-data/{id}')
            .then(r=>r.json())
            .then(d=>{{
                document.getElementById('user-count').innerText = d.count;
                document.getElementById('user-list').innerHTML = d.members;
            }});
        }}, 3000);

        function openVolumePanel(u){{
            currentTarget = u || '';
            document.getElementById('vol-target').innerText = currentTarget || '-';
            document.getElementById('vol-backdrop').style.display = 'block';

            const micKey = 'micGain';
            const playKey = 'playGain:' + currentTarget;
            const micVal = parseInt(localStorage.getItem(micKey) || '100', 10);
            const playVal = parseInt(localStorage.getItem(playKey) || '100', 10);

            const micSlider = document.getElementById('mic-slider');
            const playSlider = document.getElementById('play-slider');
            const playHint = document.getElementById('play-hint');
            micSlider.value = String(isNaN(micVal) ? 100 : micVal);
            playSlider.value = String(isNaN(playVal) ? 100 : playVal);
            document.getElementById('mic-val').innerText = micSlider.value + '%';
            document.getElementById('play-val').innerText = playSlider.value + '%';

            if (currentTarget === selfUser) {{
                playSlider.classList.add('disabled');
                playSlider.disabled = true;
                playHint.innerText = '提示：点击其他成员后可调节"听到TA的音量"。';
            }} else {{
                playSlider.classList.remove('disabled');
                playSlider.disabled = false;
                playHint.innerText = '';
            }}

            applyMicGain();
            applyPlaybackGain();
        }}

        function closeVolumePanel(){{
            document.getElementById('vol-backdrop').style.display = 'none';
        }}

        function applyMicGain(){{
            const micSlider = document.getElementById('mic-slider');
            const val = parseInt(micSlider.value, 10);
            document.getElementById('mic-val').innerText = val + '%';
            localStorage.setItem('micGain', String(val));
            fetch('/api/volume/mic', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ gain: val / 100 }})
            }});
        }}

        function applyPlaybackGain(){{
            if (!currentTarget || currentTarget === selfUser) {{
                return;
            }}
            const playSlider = document.getElementById('play-slider');
            const val = parseInt(playSlider.value, 10);
            document.getElementById('play-val').innerText = val + '%';
            localStorage.setItem('playGain:' + currentTarget, String(val));
            fetch('/api/volume/playback', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ target: currentTarget, gain: val / 100 }})
            }});
        }}

        document.addEventListener('DOMContentLoaded', () => {{
            document.getElementById('mic-slider').addEventListener('input', applyMicGain);
            document.getElementById('play-slider').addEventListener('input', applyPlaybackGain);
        }});

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') {{
                closeVolumePanel();
            }}
        }});

        function startVoiceClient(){{
            fetch('/start-voice/{id}').then(r=>r.json()).then(d=>{{
                alert(d.success ? '语音启动成功！' : '失败：'+d.error);
            }})
        }}

        function stopVoiceClient(){{
            fetch('/stop-voice').then(r=>r.json()).then(d=>{{
                alert(d.success ? '语音已关闭' : '失败：'+d.error);
            }})
        }}

        let lastChatId = 0;

        function appendChat(m){{
            const box = document.getElementById('chat-box');
            const line = document.createElement('div');
            line.className = 'chat-line';
            const t = document.createElement('div');
            t.className = 'chat-time';
            t.textContent = m.time || '';
            const u = document.createElement('div');
            u.className = 'chat-user';
            u.textContent = m.user || '';
            const text = document.createElement('div');
            text.className = 'chat-text';
            text.textContent = m.text || '';
            line.appendChild(t);
            line.appendChild(u);
            line.appendChild(text);
            box.appendChild(line);
            box.scrollTop = box.scrollHeight;
        }}

        function fetchChat(){{
            fetch('/api/chat/history/{id}?after=' + String(lastChatId))
                .then(r => r.json())
                .then(d => {{
                    if (!d.success) return;
                    const msgs = d.messages || [];
                    for (const m of msgs) {{
                        appendChat(m);
                        if (m.id && m.id > lastChatId) lastChatId = m.id;
                    }}
                }});
        }}

        function sendChat(){{
            const input = document.getElementById('chat-input');
            const text = (input.value || '').trim();
            if (!text) return;
            fetch('/api/chat/send/{id}', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ text }})
            }}).then(r => r.json()).then(d => {{
                if (d.success) {{
                    input.value = '';
                    fetchChat();
                }} else {{
                    alert('发送失败：' + (d.error || '未知错误'));
                }}
            }});
        }}

        document.addEventListener('DOMContentLoaded', () => {{
            initSidebars(); // 初始化侧边栏
            const particleSystem = new ParticleSystem(); // 初始化粒子系统
            const input = document.getElementById('chat-input');
            input.addEventListener('keydown', (e) => {{
                if (e.key === 'Enter') {{
                    sendChat();
                }}
            }});
            fetchChat();
            setInterval(fetchChat, 1200);
        }});
        
        // 侧边栏功能
        function initSidebars() {{
            const sidebarLeft = document.getElementById('sidebarLeft');
            const sidebarRight = document.getElementById('sidebarRight');
            const leftToggle = document.getElementById('sidebarLeftToggle');
            const rightToggle = document.getElementById('sidebarRightToggle');
            
            // 初始状态：收起
            sidebarLeft.classList.add('sidebar-collapsed');
            sidebarRight.classList.add('sidebar-collapsed');
            
            // 左侧边栏切换
            leftToggle.addEventListener('click', function(e) {{
                e.stopPropagation();
                if (sidebarLeft.classList.contains('sidebar-collapsed')) {{
                    sidebarLeft.classList.remove('sidebar-collapsed');
                    sidebarLeft.classList.add('sidebar-expanded');
                }} else {{
                    sidebarLeft.classList.remove('sidebar-expanded');
                    sidebarLeft.classList.add('sidebar-collapsed');
                }}
            }});
            
            // 右侧边栏切换
            rightToggle.addEventListener('click', function(e) {{
                e.stopPropagation();
                if (sidebarRight.classList.contains('sidebar-collapsed')) {{
                    sidebarRight.classList.remove('sidebar-collapsed');
                    sidebarRight.classList.add('sidebar-expanded');
                }} else {{
                    sidebarRight.classList.remove('sidebar-expanded');
                    sidebarRight.classList.add('sidebar-collapsed');
                }}
            }});
            
            // 点击外部收起侧边栏
            document.addEventListener('click', function(e) {{
                if (!sidebarLeft.contains(e.target) && !leftToggle.contains(e.target)) {{
                    sidebarLeft.classList.remove('sidebar-expanded');
                    sidebarLeft.classList.add('sidebar-collapsed');
                }}
                if (!sidebarRight.contains(e.target) && !rightToggle.contains(e.target)) {{
                    sidebarRight.classList.remove('sidebar-expanded');
                    sidebarRight.classList.add('sidebar-collapsed');
                }}
            }});
        }}
        
        // 粒子系统 - 基于index.js实现
        class ParticleSystem {{
            constructor() {{
                this.canvas = document.getElementById('particleCanvas');
                this.ctx = this.canvas.getContext('2d');
                this.particles = [];
                this.mouseX = -1000;
                this.mouseY = -1000;
                this.config = {{
                    particleSize: 2,
                    particleMargin: 2,
                    repulsionRadius: 105,
                    repulsionForce: 1.2,
                    friction: 0.15,
                    returnSpeed: 0.02,
                    maxDisplayRatio: 0.8,
                    samplingStep: 5,
                    mobileRepulsionRadius: 78
                }};
                this.isMobile = window.innerWidth <= 768;
                this.init();
            }}
            
            init() {{
                console.log('初始化粒子系统...');
                this.resizeCanvas();
                window.addEventListener('resize', () => this.resizeCanvas());
                document.addEventListener('mousemove', (e) => this.handleMouseMove(e));
                document.addEventListener('touchmove', (e) => this.handleTouchMove(e));
                
                // 测试Canvas是否工作
                this.ctx.fillStyle = 'red';
                this.ctx.fillRect(50, 50, 100, 100);
                console.log('Canvas测试矩形已绘制');
                
                // 先创建一些随机粒子作为备用
                this.createRandomParticles();
                console.log(`创建了 ${{this.particles.length}} 个随机粒子`);
                
                // 启动动画
                this.animate();
                console.log('动画已启动');
                
                // 然后尝试加载图片
                this.loadImageAndCreateParticles();
            }}
            
            resizeCanvas() {{
                this.canvas.width = window.innerWidth;
                this.canvas.height = window.innerHeight;
            }}
            
            handleMouseMove(e) {{
                this.mouseX = e.clientX;
                this.mouseY = e.clientY;
            }}
            
            handleTouchMove(e) {{
                if (e.touches.length > 0) {{
                    this.mouseX = e.touches[0].clientX;
                    this.mouseY = e.touches[0].clientY;
                }}
            }}
            
            loadImageAndCreateParticles() {{
                console.log('开始加载图片并创建粒子...');
                const img = new Image();
                img.src = '/static/images/img/Yan.png';
                console.log('图片路径:', img.src);
                
                img.onload = () => {{
                    console.log('图片加载成功，图片尺寸:', img.width, 'x', img.height);
                    console.log('清空现有粒子并创建新粒子...');
                    this.particles = []; // 清空现有粒子
                    this.createParticlesFromImage(img);
                    console.log(`从图片创建了 ${{this.particles.length}} 个粒子`);
                }};
                img.onerror = (error) => {{
                    console.log('图片加载失败，错误:', error);
                    console.log('保持使用随机粒子');
                    // 保持现有的随机粒子
                }};
            }}
            
            createParticlesFromImage(img) {{
                console.log('开始从图片创建粒子...');
                const tempCanvas = document.createElement('canvas');
                const tempCtx = tempCanvas.getContext('2d');
                
                const canvasWidth = window.innerWidth;
                const canvasHeight = window.innerHeight;
                const maxDisplayWidth = canvasWidth * this.config.maxDisplayRatio;
                const maxDisplayHeight = canvasHeight * this.config.maxDisplayRatio;
                
                let width = img.width;
                let height = img.height;
                console.log('原始图片尺寸:', width, 'x', height);
                
                if (width > maxDisplayWidth || height > maxDisplayHeight) {{
                    const ratio = Math.min(maxDisplayWidth / width, maxDisplayHeight / height);
                    width *= ratio;
                    height *= ratio;
                    console.log('调整后尺寸:', width, 'x', height, '比例:', ratio);
                }}
                
                tempCanvas.width = width;
                tempCanvas.height = height;
                tempCtx.drawImage(img, 0, 0, width, height);
                
                const imgData = tempCtx.getImageData(0, 0, width, height);
                console.log('获取图像数据，尺寸:', imgData.width, 'x', imgData.height);
                
                const offsetX = (canvasWidth - width) / 2;
                const offsetY = (canvasHeight - height) / 2;
                console.log('偏移量:', offsetX, offsetY);
                
                let particleCount = 0;
                for (let y = 0; y < height; y += this.config.samplingStep) {{
                    for (let x = 0; x < width; x += this.config.samplingStep) {{
                        const alpha = imgData.data[(y * width + x) * 4 + 3];
                        if (alpha > 64) {{
                            const brightness = this.getPixelBrightness(imgData, x, y);
                            const particle = new Particle(
                                x + offsetX,
                                y + offsetY,
                                this.config,
                                brightness > 128 ? 'light' : 'dark'
                            );
                            this.particles.push(particle);
                            particleCount++;
                        }}
                    }}
                }}
                console.log(`从图片创建了 ${{particleCount}} 个粒子`);
            }}
            
            createRandomParticles() {{
                const particleCount = 200;
                for (let i = 0; i < particleCount; i++) {{
                    const x = Math.random() * window.innerWidth;
                    const y = Math.random() * window.innerHeight;
                    this.particles.push(new Particle(x, y, this.config, 'light'));
                }}
            }}
            
            getPixelBrightness(imgData, x, y) {{
                const i = (y * imgData.width + x) * 4;
                return (imgData.data[i] + imgData.data[i + 1] + imgData.data[i + 2]) / 3;
            }}
            
            animate() {{
                // 清除画布
                this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                
                // 绘制所有粒子
                this.particles.forEach(particle => {{
                    particle.update(this.mouseX, this.mouseY, this.isMobile);
                    particle.draw(this.ctx);
                }});
                
                // 调试：每60帧输出一次
                if (!this.frameCount) this.frameCount = 0;
                this.frameCount++;
                if (this.frameCount % 60 === 0) {{
                    console.log(`动画运行中，当前粒子数: ${{this.particles.length}}`);
                }}
                
                // 继续动画循环
                requestAnimationFrame(() => this.animate());
            }}
        }}
        
        class Particle {{
            constructor(x, y, config, colorType) {{
                this.x = x;
                this.y = y;
                this.originalX = x;
                this.originalY = y;
                this.vx = 0;
                this.vy = 0;
                this.config = config;
                this.colorType = colorType;
                this.opacity = Math.random() * 0.4 + 0.4;
            }}
            
            update(mouseX, mouseY, isMobile) {{
                const dx = this.x - mouseX;
                const dy = this.y - mouseY;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                const repulsionRadius = isMobile ? this.config.mobileRepulsionRadius : this.config.repulsionRadius;
                
                if (distance < repulsionRadius) {{
                    const angle = Math.atan2(dy, dx);
                    const ratio = (repulsionRadius - distance) / repulsionRadius;
                    const force = ratio * ratio * this.config.repulsionForce;
                    
                    this.vx += Math.cos(angle) * force;
                    this.vy += Math.sin(angle) * force;
                }}
                
                const returnX = (this.originalX - this.x) * this.config.returnSpeed;
                const returnY = (this.originalY - this.y) * this.config.returnSpeed;
                this.vx += returnX;
                this.vy += returnY;
                
                this.vx *= (1 - this.config.friction);
                this.vy *= (1 - this.config.friction);
                
                this.x += this.vx;
                this.y += this.vy;
            }}
            
            draw(ctx) {{
                const color = this.colorType === 'light' ? 
                    `rgba(45, 212, 191, ${{this.opacity}})` : 
                    `rgba(139, 92, 246, ${{this.opacity}})`;
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.config.particleSize, 0, Math.PI * 2);
                ctx.fill();
                
                // 调试：每100个粒子输出一次位置信息
                if (Math.random() < 0.01) {{
                    console.log(`粒子位置: (${{Math.round(this.x)}}, ${{Math.round(this.y)}}), 颜色: ${{this.colorType}}, 透明度: ${{this.opacity}}`);
                }}
            }}
        }}
    </script>
    </body>
    </html>
    '''

# API路由
@app.route('/api/chat/history/<room_id>')
def chat_history(room_id):
    if "user" not in session:
        return {"success": False, "error": "未登录", "messages": []}
    after = request.args.get("after")
    try:
        after = int(after) if after is not None else 0
    except:
        after = 0
    room = chat_rooms.get(room_id)
    if room is None:
        room = {"next_id": 1, "messages": []}
        chat_rooms[room_id] = room
    with chat_lock:
        msgs = [m for m in room["messages"] if m["id"] > after]
    return {"success": True, "messages": msgs[-100:]}

@app.route('/api/chat/send/<room_id>', methods=['POST'])
def chat_send(room_id):
    if "user" not in session:
        return {"success": False, "error": "未登录"}
    text = None
    if request.is_json:
        text = request.json.get("text")
    if text is None:
        text = request.form.get("text")
    if text is None:
        return {"success": False, "error": "参数错误"}
    text = str(text).strip()
    if not text:
        return {"success": False, "error": "消息不能为空"}
    if len(text) > 500:
        return {"success": False, "error": "消息过长"}

    room = chat_rooms.get(room_id)
    if room is None:
        room = {"next_id": 1, "messages": []}
        chat_rooms[room_id] = room
    prof = get_user_profiles([session["user"]]).get(session["user"]) or {}
    chat_user = (prof.get("nickname") or session["user"])
    with chat_lock:
        msg_id = room["next_id"]
        room["next_id"] += 1
        room["messages"].append({
            "id": msg_id,
            "user": chat_user,
            "text": text,
            "time": datetime.now().strftime("%H:%M:%S")
        })
        if len(room["messages"]) > 500:
            room["messages"] = room["messages"][-500:]

    return {"success": True}

@app.route('/api/volume/mic', methods=['POST'])
def set_mic_volume():
    if "user" not in session:
        return {"success": False, "error": "未登录"}
    gain = None
    if request.is_json:
        gain = request.json.get("gain")
    if gain is None:
        gain = request.form.get("gain") or request.args.get("gain")
    try:
        gain = float(gain)
    except:
        return {"success": False, "error": "参数错误"}
    gain = max(0.0, min(2.0, gain))
    ok, err = send_voice_control(session["user"], {"type": "mic", "gain": gain})
    return {"success": ok, "error": err}

@app.route('/api/volume/playback', methods=['POST'])
def set_playback_volume():
    if "user" not in session:
        return {"success": False, "error": "未登录"}
    target = None
    gain = None
    if request.is_json:
        target = request.json.get("target")
        gain = request.json.get("gain")
    if target is None:
        target = request.form.get("target") or request.args.get("target")
    if gain is None:
        gain = request.form.get("gain") or request.args.get("gain")
    if not target:
        return {"success": False, "error": "参数错误"}
    try:
        gain = float(gain)
    except:
        return {"success": False, "error": "参数错误"}
    gain = max(0.0, min(2.0, gain))
    ok, err = send_voice_control(session["user"], {"type": "playback", "target": str(target), "gain": gain})
    return {"success": ok, "error": err}

# 语音控制相关函数
def allocate_local_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def get_voice_entry(username):
    entry = voice_processes.get(username)
    if entry is None:
        return None
    if isinstance(entry, dict):
        return entry
    return {"proc": entry, "control_port": None}

def terminate_voice_entry(entry):
    if not entry:
        return
    proc = entry.get("proc") if isinstance(entry, dict) else entry
    if proc is None:
        return
    try:
        proc.terminate()
    except:
        pass

def send_voice_control(username, payload):
    entry = get_voice_entry(username)
    if not entry or not entry.get("control_port"):
        return False, "语音客户端未运行"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect(("127.0.0.1", int(entry["control_port"])))
        msg = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        s.sendall(msg)
        s.close()
        return True, None
    except Exception as e:
        return False, str(e)

# 语音相关路由
@app.route('/start-voice/<room_id>')
def start_voice(room_id):
    if "user" not in session:
        return {"success": False, "error": "未登录"}

    username = session['user']
    client_path = os.path.join(os.path.dirname(__file__), 'client.py')

    try:
        existing = get_voice_entry(username)
        terminate_voice_entry(existing)

        control_port = allocate_local_port()

        if os.name == 'nt':
            proc = subprocess.Popen([sys.executable, client_path, username, room_id, str(control_port)], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            proc = subprocess.Popen([sys.executable, client_path, username, room_id, str(control_port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        voice_processes[username] = {"proc": proc, "control_port": control_port}
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route('/stop-voice')
def stop_voice():
    if "user" not in session:
        return {"success": False, "error": "未登录"}
    user = session['user']
    if user in voice_processes:
        try:
            terminate_voice_entry(get_voice_entry(user))
            del voice_processes[user]
            return {"success": True}
        except:
            return {"success": False, "error": "关闭失败"}
    return {"success": False, "error": "未运行"}

@app.route('/leave-room/<room_id>')
def leave_room(room_id):
    if "user" not in session: return redirect("/login")
    user = session["user"]
    if room_id in room_users:
        room_users[room_id].discard(user)
    try:
        stop_voice()
    except:
        pass
    return redirect("/")

@app.route('/room-data/<id>')
def room_data(id):
    voice_users = []
    speaking_user = None
    try:
        res = requests.get(f'http://127.0.0.1:5001/api/room-users/{id}', timeout=1)
        if res.status_code == 200:
            d = res.json()
            voice_users = d.get('users', [])
            speaking_user = d.get('speaking')
    except:
        pass

    web_users = room_users.get(id, set())
    all_users = web_users | set(voice_users)

    profiles = get_user_profiles(all_users)
    members = ''
    for u in sorted(all_users):
        safe_u = u.replace("'", "").replace('"', "")
        label = format_user_label(u, profiles.get(u))
        info_link = f"<a class='user-info' href='/user/{safe_u}' onclick=\"event.stopPropagation();\">资料</a>"
        if u == speaking_user:
            members += f"<li class='user-item speaking' onclick=\"openVolumePanel('{safe_u}')\"><div class='user-main'><span class='badge badge-green'>说话</span>{label}</div><div class='user-meta'>🎤 {info_link}</div></li>"
        elif u in voice_users:
            members += f"<li class='user-item voice' onclick=\"openVolumePanel('{safe_u}')\"><div class='user-main'><span class='badge badge-teal'>语音</span>{label}</div><div class='user-meta'>✅ {info_link}</div></li>"
        else:
            members += f"<li class='user-item online' onclick=\"openVolumePanel('{safe_u}')\"><div class='user-main'><span class='badge badge-gray'>在线</span>{label}</div><div class='user-meta'>• {info_link}</div></li>"

    return {"count": len(all_users), "members": members}

# 传统创建房间路由（保留兼容性）
@app.route('/create', methods=['GET','POST'])
def create():
    if "user" not in session: return redirect("/login")
    if request.method == 'POST':
        name = request.form['name']
        error = validate_room_name(name)
        if error: return f"<h3>{error}</h3>"
        
        room_id, error = create_room(name, session['user'])
        if error:
            return f"<h3>{error}</h3>"
        
        return redirect("/")
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>小T语音 - 创建房间</title>
        <style>
            *{margin:0;padding:0;box-sizing:border-box}
            body{background:#111827;color:#fff;font-family:Segoe UI,微软雅黑;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:28px}
            a{text-decoration:none;color:#2dd4bf}
            .wrap{width:100%;max-width:520px}
            .brand{color:#2dd4bf;font-size:24px;font-weight:900;letter-spacing:.5px}
            .sub{color:#9ca3af;margin-top:6px;font-size:13px}
            .card{margin-top:18px;background:#1f2937;border:1px solid #111827;border-radius:16px;padding:22px;box-shadow:0 0 24px #0006}
            .field{margin-top:12px}
            .label{font-size:12px;color:#cbd5e1;margin-bottom:6px}
            input{width:100%;padding:12px 14px;background:#111827;border:1px solid #374151;color:#fff;border-radius:10px;font-size:14px;outline:none}
            input:focus{border-color:#2dd4bf;box-shadow:0 0 0 3px #2dd4bf22}
            .row{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap}
            .btn{flex:1;min-width:160px;background:#2dd4bf;color:#111;font-weight:900;border:none;padding:12px 14px;border-radius:10px;cursor:pointer;text-align:center}
            .btn:hover{filter:brightness(1.03)}
            .btn-ghost{background:transparent;color:#e5e7eb;border:1px solid #374151}
        </style>
    </head>
    <body>
        <div class="wrap">
            <div class="brand">创建房间</div>
            <div class="sub">输入房间名称后创建，创建完成会返回首页列表</div>
            <div class="card">
                <form method="post">
                    <div class="field">
                        <div class="label">房间名称</div>
                        <input name="name" placeholder="输入房间名称" required>
                    </div>
                    <div class="row">
                        <button class="btn" type="submit">创建</button>
                        <a class="btn btn-ghost" href="/">返回</a>
                    </div>
                </form>
            </div>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    import logging
    # 配置日志级别，只输出警告及以上级别的信息
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.WARNING)
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
