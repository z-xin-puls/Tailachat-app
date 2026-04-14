# 主页和地图路由
from flask import Blueprint, request, redirect, render_template, session, jsonify
from models.database import get_db_connection
from models.user import get_user_profiles
from models.room import get_all_rooms, create_room, create_room_with_fortress
from utils.validators import validate_room_name
from utils.helpers import html_escape
import json
import requests

#  Alias for consistency with other code
get_db = get_db_connection

main_bp = Blueprint('main', __name__)

def get_real_online_count(room_id):
    """Get real online user count by calling app.py's API endpoint"""
    try:
        print(f"DEBUG: Getting online count for room {room_id}")
        #  Call app.py's room_data endpoint via HTTP
        res = requests.get(f'http://127.0.0.1:5000/room-data/{room_id}', timeout=2)
        print(f"DEBUG: API response status: {res.status_code}")
        if res.status_code == 200:
            result = res.json()
            print(f"DEBUG: API response data: {result}")
            count = result.get('count', 0)
            print(f"DEBUG: Extracted count for room {room_id}: {count}")
            return count
        else:
            print(f"DEBUG: API response text: {res.text}")
            return 0
    except Exception as e:
        print(f"DEBUG: Exception in get_real_online_count: {e}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return 0

@main_bp.route('/')
def index():
    if "user" not in session:
        return redirect("/login")

    prof = get_user_profiles([session["user"]]).get(session["user"]) or {}
    display_user = (prof.get("nickname") or session["user"])

    rooms = get_all_rooms()
    
    # 为每个房间添加模拟的在线人数（实际项目中应该从实时数据获取）
    import random
    for room in rooms:
        # 模拟在线人数：1-10人
        room['online_count'] = random.randint(1, 10)
    
    # 获取用户相关的房间（用户创建的或加入的）
    user_rooms = [room for room in rooms if room['owner'] == session['user']]
    
    # 获取据点信息
    fortress_list = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fortresses ORDER BY id")
        fortresses = cursor.fetchall()
        
        # 转换为字典格式
        for fortress in fortresses:
            fortress_dict = {
                'id': fortress[0],
                'name': fortress[1], 
                'x': float(fortress[2]),
                'y': float(fortress[3]),
                'radius': float(fortress[4]),
                'color': fortress[5],
                'description': fortress[6] if len(fortress) > 6 else ''
            }
            fortress_list.append(fortress_dict)
        
        print(f"成功获取 {len(fortress_list)} 个据点")
        conn.close()
        
    except Exception as e:
        print(f"获取据点数据失败: {e}")
        # 如果失败，创建一些测试数据
        fortress_list = [
            {'id': 1, 'name': '中央房间', 'x': 50.0, 'y': 50.0, 'radius': 25.0, 'color': '#f59e0b', 'description': '主要房间，连接所有区域'},
            {'id': 2, 'name': '北方房间', 'x': 50.0, 'y': 20.0, 'radius': 20.0, 'color': '#3b82f6', 'description': '寒冷地区的房间'},
            {'id': 3, 'name': '南方房间', 'x': 50.0, 'y': 80.0, 'radius': 18.0, 'color': '#10b981', 'description': '温暖地区的房间'}
        ]
        print("使用测试据点数据")

    return render_template('main/index.html', 
                         current_user=html_escape(display_user),
                         rooms=rooms, 
                         user_rooms=user_rooms, 
                         fortresses=fortress_list)
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>泰拉通讯 - 地图</title>
        <style>
            *{{margin:0;padding:0;box-sizing:border-box}}
            body{{background:#111827;color:#fff;font-family:Segoe UI,微软雅黑;overflow:hidden}}
            .topbar{{position:fixed;top:0;left:0;right:0;z-index:1000;background:#1f2937;border-bottom:1px solid #374151;padding:12px 20px;display:flex;align-items:center;justify-content:space-between}}
            .title{{color:#2dd4bf;font-size:20px;font-weight:900}}
            .user-info{{color:#cbd5e1;font-size:14px}}
            .actions{{display:flex;gap:10px}}
            .btn{{display:inline-flex;align-items:center;justify-content:center;padding:8px 12px;border-radius:8px;border:1px solid transparent;font-weight:700;cursor:pointer;font-size:13px}}
            .btn-teal{{background:#2dd4bf;color:#111}}
            .btn-ghost{{background:transparent;color:#e5e7eb;border-color:#374151}}
            .zoom-controls{{position:fixed;bottom:20px;right:20px;z-index:1000;display:flex;flex-direction:column;gap:8px}}
            .zoom-btn{{width:40px;height:40px;border-radius:50%;background:#1f2937;border:1px solid #374151;color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:18px;transition:all 0.2s ease}}
            .zoom-btn:hover{{background:#2dd4bf;color:#111;border-color:#2dd4bf}}
            .zoom-level{{color:#cbd5e1;font-size:12px;text-align:center;background:#1f2937;border:1px solid #374151;border-radius:8px;padding:4px 8px}}
            .map-container{{position:relative;width:100vw;height:100vh;overflow:hidden;cursor:grab}}
            .map{{position:absolute;width:4081px;height:5488px;background:url('/static/images/map/Taila.png') no-repeat center;background-size:contain}}
            .outpost{{position:absolute;width:60px;height:60px;border-radius:50%;background:#2dd4bf;border:3px solid #fff;cursor:pointer;display:flex;align-items:center;justify-content:center;transform:translate(-50%,-50%);transition:all 0.3s ease;z-index:10}}
            .outpost:hover{{transform:translate(-50%,-50%) scale(1.1);box-shadow:0 0 20px #2dd4bf}}
            .outpost-icon{{font-size:24px}}
            .outpost-tooltip{{position:absolute;bottom:70px;left:50%;transform:translateX(-50%);background:#1f2937;border:1px solid #374151;border-radius:8px;padding:8px 12px;white-space:nowrap;opacity:0;pointer-events:none;transition:opacity 0.3s;z-index:100}}
            .outpost:hover .outpost-tooltip{{opacity:1}}
            .outpost-name{{color:#fff;font-weight:700;font-size:14px}}
            .outpost-owner{{color:#9ca3af;font-size:12px}}
            .create-modal{{display:none;position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1f2937;border:1px solid #374151;border-radius:16px;padding:24px;z-index:2000}}
            .modal-overlay{{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:#0008;z-index:1999}}
            .modal-title{{color:#2dd4bf;font-size:18px;font-weight:900;margin-bottom:16px}}
            .field{{margin-bottom:16px}}
            .label{{display:block;color:#cbd5e1;font-size:12px;margin-bottom:6px}}
            .input{{width:100%;padding:10px 12px;background:#111827;border:1px solid #374151;color:#fff;border-radius:8px;font-size:14px}}
            .room-info-modal{{display:none;position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1f2937;border:1px solid #374151;border-radius:16px;padding:48px;z-index:2000;width:900px;height:700px;overflow-y:auto;box-shadow:0 20px 25px -5px rgba(0, 0, 0, 0.1),0 10px 10px -5px rgba(0, 0, 0, 0.04);backdrop-filter:blur(8px)}}
            .room-info-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}}
            .room-info-title{{color:#2dd4bf;font-size:18px;font-weight:900}}
            .room-info-close{{background:transparent;border:none;color:#9ca3af;font-size:24px;cursor:pointer;padding:0;width:32px;height:32px;display:flex;align-items:center;justify-content:center;border-radius:8px}}
            .room-info-close:hover{{background:#374151;color:#fff}}
            .room-info-content{{margin-bottom:20px}}
            .room-info-name{{color:#fff;font-size:16px;font-weight:700;margin-bottom:8px}}
            .room-info-details{{color:#cbd5e1;font-size:14px;line-height:1.5}}
            .room-info-actions{{display:flex;gap:10px;justify-content:flex-end}}
            .my-outposts-modal{{display:none;position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1f2937;border:1px solid #374151;border-radius:16px;padding:24px;z-index:2000;min-width:400px;max-height:500px;overflow-y:auto}}
            .my-outposts-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}}
            .my-outposts-title{{color:#2dd4bf;font-size:18px;font-weight:900}}
            .my-outposts-close{{background:transparent;border:none;color:#9ca3af;font-size:24px;cursor:pointer;padding:0;width:32px;height:32px;display:flex;align-items:center;justify-content:center;border-radius:8px}}
            .my-outposts-close:hover{{background:#374151;color:#fff}}
            .outpost-list{{margin-bottom:16px}}
            .outpost-item{{background:#111827;border:1px solid #374151;border-radius:8px;padding:12px;margin-bottom:8px;cursor:pointer;transition:all 0.2s ease}}
            .outpost-item:hover{{background:#374151;border-color:#2dd4bf}}
            .outpost-item-name{{color:#fff;font-weight:700;font-size:14px;margin-bottom:4px}}
            .outpost-item-details{{color:#cbd5e1;font-size:12px}}
            .my-outposts-actions{{display:flex;gap:10px;justify-content:flex-end}}
            .modal-actions{{display:flex;gap:10px;justify-content:flex-end;margin-top:20px}}
            .tactical-sidebar{{position:fixed;top:50%;right:20px;transform:translateY(-50%);background:#1f2937;border:1px solid #374151;border-radius:12px;z-index:1000;transition:all 0.3s ease;max-width:300px}}
            .sidebar-collapsed{{width:50px;height:50px}}
            .sidebar-expanded{{width:280px;max-height:500px;overflow-y:auto}}
            .sidebar-toggle{{width:100%;height:50px;background:#2dd4bf;color:#111;border:none;border-radius:12px 12px 0 0;cursor:pointer;font-size:18px;font-weight:900;display:flex;align-items:center;justify-content:center;transition:all 0.3s ease}}
            .sidebar-toggle:hover{{background:#26b5a6}}
            .sidebar-content{{padding:16px;display:none}}
            .sidebar-expanded .sidebar-content{{display:block}}
            .sidebar-title{{color:#2dd4bf;font-size:16px;font-weight:900;margin-bottom:16px;text-align:center}}
            .sidebar-section{{margin-bottom:20px}}
            .sidebar-section-title{{color:#cbd5e1;font-size:12px;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.05em}}
            .sidebar-btn{{width:100%;padding:10px;background:#111827;border:1px solid #374151;color:#fff;border-radius:8px;cursor:pointer;font-size:14px;margin-bottom:8px;transition:all 0.2s ease;text-align:left}}
            .sidebar-btn:hover{{background:#374151;border-color:#2dd4bf}}
            .sidebar-outpost-list{{max-height:200px;overflow-y:auto}}
            .sidebar-outpost-item{{background:#111827;border:1px solid #374151;border-radius:6px;padding:8px;margin-bottom:6px;cursor:pointer;transition:all 0.2s ease}}
            .sidebar-outpost-item:hover{{background:#374151;border-color:#2dd4bf}}
            .sidebar-outpost-name{{color:#fff;font-size:12px;font-weight:700;margin-bottom:2px}}
            .sidebar-outpost-info{{color:#9ca3af;font-size:10px}}
            .white-ring{{position:absolute;border-radius:50%;pointer-events:none;z-index:1}}
            .ring-layer{{position:absolute;border-radius:50%;border:2px solid rgba(255,255,255,0.6);pointer-events:none}}
            .ring-small{{width:100px;height:100px;animation:ring-breathe-small 4s ease-in-out infinite}}
            .ring-medium{{width:140px;height:140px;animation:ring-breathe-medium 5s ease-in-out infinite}}
            .ring-large{{width:180px;height:180px;animation:ring-expand-large 6s ease-in-out infinite}}
            .ring-inner{{width:70%;height:70%;border:1.5px solid rgba(255,255,255,0.8);animation:ring-pulse-inner 2s ease-in-out infinite}}
            .ring-middle{{width:85%;height:85%;border:3px solid rgba(255,255,255,0.4);animation:ring-pulse-middle 3s ease-in-out infinite}}
            .ring-outer{{width:100%;height:100%;border:0.5px solid rgba(255,255,255,0.2);animation:ring-pulse-outer 4s ease-in-out infinite}}
            .fortress-ring{{position:absolute;border-radius:50%;pointer-events:none;z-index:2}}
            .fortress-ring-layer{{position:absolute;border-radius:50%;border:4px solid;pointer-events:none}}
            .fortress-ring-small{{width:200px;height:200px;animation:fortress-breathe-small 4s ease-in-out infinite}}
            .fortress-ring-medium{{width:300px;height:300px;animation:fortress-breathe-medium 5s ease-in-out infinite}}
            .fortress-ring-large{{width:400px;height:400px;animation:fortress-expand-large 6s ease-in-out infinite}}
            .fortress-ring-inner{{width:80%;height:80%;border:5px solid;animation:fortress-pulse-inner 2s ease-in-out infinite}}
            .fortress-ring-middle{{width:90%;height:90%;border:8px solid;animation:fortress-pulse-middle 3s ease-in-out infinite}}
            .fortress-ring-outer{{width:100%;height:100%;border:3px solid;animation:fortress-pulse-outer 4s ease-in-out infinite}}
            @keyframes ring-breathe-small{{0%,100%{{opacity:0.3;transform:translate(-50%,-50%) scale(0.9)}}50%{{opacity:0.8;transform:translate(-50%,-50%) scale(1.1)}}}}
            @keyframes ring-breathe-medium{{0%,100%{{opacity:0.4;transform:translate(-50%,-50%) scale(0.85)}}50%{{opacity:0.9;transform:translate(-50%,-50%) scale(1.15)}}}}
            @keyframes ring-expand-large{{0%{{opacity:0.5;transform:translate(-50%,-50%) scale(0.8)}}25%{{opacity:1;transform:translate(-50%,-50%) scale(1.2)}}50%{{opacity:0.3;transform:translate(-50%,-50%) scale(1.3)}}75%{{opacity:1;transform:translate(-50%,-50%) scale(1.2)}}100%{{opacity:0.5;transform:translate(-50%,-50%) scale(0.8)}}}}
            @keyframes ring-pulse-inner{{0%,100%{{opacity:0.6;transform:translate(-50%,-50%) scale(0.95)}}50%{{opacity:1;transform:translate(-50%,-50%) scale(1.05)}}}}
            @keyframes ring-pulse-middle{{0%,100%{{opacity:0.3;transform:translate(-50%,-50%) scale(0.97)}}50%{{opacity:0.7;transform:translate(-50%,-50%) scale(1.03)}}}}
            @keyframes ring-pulse-outer{{0%,100%{{opacity:0.1;transform:translate(-50%,-50%) scale(0.99)}}50%{{opacity:0.3;transform:translate(-50%,-50%) scale(1.01)}}}}
            @keyframes fortress-breathe-small{{0%,100%{{opacity:0.6;transform:translate(-50%,-50%) scale(0.95)}}50%{{opacity:0.9;transform:translate(-50%,-50%) scale(1.05)}}}}
            @keyframes fortress-breathe-medium{{0%,100%{{opacity:0.6;transform:translate(-50%,-50%) scale(0.9)}}50%{{opacity:0.9;transform:translate(-50%,-50%) scale(1.1)}}}}
            @keyframes fortress-expand-large{{0%{{opacity:0.7;transform:translate(-50%,-50%) scale(0.85)}}25%{{opacity:0.9;transform:translate(-50%,-50%) scale(1.1)}}50%{{opacity:0.6;transform:translate(-50%,-50%) scale(1.15)}}75%{{opacity:0.9;transform:translate(-50%,-50%) scale(1.1)}}100%{{opacity:0.7;transform:translate(-50%,-50%) scale(0.85)}}}}
            @keyframes fortress-pulse-inner{{0%,100%{{opacity:0.8;transform:translate(-50%,-50%) scale(0.95)}}50%{{opacity:1;transform:translate(-50%,-50%) scale(1.05)}}}}
            @keyframes fortress-pulse-middle{{0%,100%{{opacity:0.6;transform:translate(-50%,-50%) scale(0.97)}}50%{{opacity:0.8;transform:translate(-50%,-50%) scale(1.03)}}}}
            @keyframes fortress-pulse-outer{{0%,100%{{opacity:0.4;transform:translate(-50%,-50%) scale(0.99)}}50%{{opacity:0.6;transform:translate(-50%,-50%) scale(1.01)}}}}
        </style>
    </head>
    <body>
        <div class="topbar">
            <div>
                <div class="title">🗺️ 语音地图</div>
                <div class="user-info">欢迎，{html_escape(display_user)}</div>
            </div>
            <div class="actions">
            </div>
        </div>

        <div class="map-container" id="mapContainer">
            <div class="map" id="map">
                <!-- 房间将动态添加到这里 -->
            </div>
        </div>

        <!-- 缩放控制 -->
        <div class="zoom-controls">
            <button class="zoom-btn" onclick="zoomIn()">+</button>
            <div class="zoom-level" id="zoomLevel">100%</div>
            <button class="zoom-btn" onclick="zoomOut()">−</button>
            <button class="zoom-btn" onclick="resetZoom()">⟲</button>
        </div>

        <!-- 泰拉战术侧边栏 -->
        <div class="tactical-sidebar sidebar-collapsed" id="tacticalSidebar">
            <button class="sidebar-toggle" onclick="toggleSidebar()">
                <span id="sidebarToggleIcon">⚔️</span>
            </button>
            <div class="sidebar-content">
                <div class="sidebar-title">🎯 泰拉战术</div>
                
                <div class="sidebar-section">
                    <div class="sidebar-section-title">快速操作</div>
                    <button class="sidebar-btn" onclick="window.location.href='/profile'">
                        👤 个人中心
                    </button>
                    <button class="sidebar-btn" onclick="showMyOutpostsModal()">
                        🏰 我的房间
                    </button>
                </div>
                
                <div class="sidebar-section">
                    <div class="sidebar-section-title">房间战况</div>
                    <div class="sidebar-outpost-list" id="sidebarOutpostList">
                        <!-- 房间列表将动态添加到这里 -->
                    </div>
                </div>
            </div>
        </div>

        <!-- 创建房间弹窗 -->
        <div class="modal-overlay" id="modalOverlay"></div>
        <div class="create-modal" id="createModal">
            <div class="modal-title">🏰 创建房间</div>
            <form id="createForm">
                <div class="field">
                    <label class="label">房间名称</label>
                    <input type="text" name="name" class="input" placeholder="输入房间名称" required>
                </div>
                <input type="hidden" name="x" id="outpostX">
                <input type="hidden" name="y" id="outpostY">
                <div class="modal-actions">
                    <button type="button" class="btn btn-ghost" onclick="closeCreateModal()">取消</button>
                    <button type="submit" class="btn btn-teal">创建房间</button>
                </div>
            </form>
        </div>

        <!-- 房间信息弹窗 -->
        <div class="modal-overlay" id="roomInfoOverlay"></div>
        <div class="room-info-modal" id="roomInfoModal">
            <canvas id="modalParticleCanvas" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;opacity:0.8;"></canvas>
            <div class="room-info-header">
                <div class="room-info-title">🏰 据点信息</div>
                <button class="room-info-close" onclick="closeRoomInfoModal()">&times;</button>
            </div>
            <div class="room-info-content">
                <div class="room-info-name" id="roomInfoName"></div>
                <div class="room-info-details" id="roomInfoDetails"></div>
                
                <!-- 创建房间表单 -->
                <div class="fortress-create-room" id="fortressCreateRoom" style="margin-top: 20px; padding: 15px; background: #111827; border-radius: 8px; border: 1px solid #374151;">
                    <div style="color: #2dd4bf; font-size: 14px; font-weight: bold; margin-bottom: 10px;">🏠 在此据点创建房间</div>
                    <form id="fortressCreateForm">
                        <div style="margin-bottom: 10px;">
                            <label style="color: #cbd5e1; font-size: 12px; display: block; margin-bottom: 5px;">房间名称</label>
                            <input type="text" name="name" id="fortressRoomName" required 
                                   style="width: 100%; padding: 8px; background: #1f2937; border: 1px solid #374151; border-radius: 4px; color: #fff; font-size: 14px;">
                        </div>
                        <input type="hidden" name="fortress_id" id="fortressId">
                        <input type="hidden" name="x" id="fortressX">
                        <input type="hidden" name="y" id="fortressY">
                        <button type="submit" class="btn btn-teal" style="padding: 8px 16px; font-size: 12px;">创建房间</button>
                    </form>
                </div>
                
                <!-- 据点房间列表 -->
                <div class="fortress-rooms" id="fortressRooms" style="margin-top: 20px;">
                    <div style="color: #2dd4bf; font-size: 14px; font-weight: bold; margin-bottom: 10px;">🏠 据点房间列表</div>
                    <div id="fortressRoomList" style="max-height: 200px; overflow-y: auto;">
                        <!-- 房间列表将动态生成 -->
                    </div>
                </div>
            </div>
            <div class="room-info-actions">
                <button type="button" class="btn btn-ghost" onclick="closeRoomInfoModal()">关闭</button>
            </div>
        </div>

        <!-- 我的房间弹窗 -->
        <div class="modal-overlay" id="myOutpostsOverlay"></div>
        <div class="my-outposts-modal" id="myOutpostsModal">
            <div class="my-outposts-header">
                <div class="my-outposts-title">🏰 我的房间</div>
                <button class="my-outposts-close" onclick="closeMyOutpostsModal()">&times;</button>
            </div>
            <div class="outpost-list" id="myOutpostsList">
                <!-- 房间列表将动态添加到这里 -->
            </div>
            <div class="my-outposts-actions">
                <button type="button" class="btn btn-ghost" onclick="closeMyOutpostsModal()">关闭</button>
            </div>
        </div>

        <script>
            // 房间数据
            var rooms = ''' + json.dumps([{'id': r['id'], 'name': r['name'], 'owner': r['owner'], 'x': r['x'], 'y': r['y'], 'online_count': r['online_count']} for r in rooms]) + ''';
            // 用户房间数据
            var userRooms = ''' + json.dumps([{'id': r['id'], 'name': r['name'], 'owner': r['owner'], 'x': r['x'], 'y': r['y'], 'online_count': r['online_count']} for r in user_rooms]) + ''';
            // 据点数据
            var fortresses = ''' + json.dumps(fortress_list) + ''';
            
            // 地图拖动功能
            var isDragging = false;
            var startX = 0, startY = 0;
            var mapX = 0, mapY = 0;
            var hasMoved = false;
            var scale = 1;
            var mapContainer = document.getElementById('mapContainer');
            var map = document.getElementById('map');
            
            function centerMap() {
                mapX = (window.innerWidth - 4081 * scale) / 2;
                mapY = (window.innerHeight - 5488 * scale) / 2;
                updateMapPosition();
            }
            
            function updateMapPosition() {
                // 计算地图的实际尺寸（考虑缩放）
                var mapWidth = 4081 * scale;
                var mapHeight = 5488 * scale;
                var containerWidth = window.innerWidth;
                var containerHeight = window.innerHeight;
                
                // 计算边界限制
                var minX, minY, maxX, maxY;
                
                if (mapWidth <= containerWidth) {
                    // 地图宽度小于等于容器宽度时，水平居中
                    minX = (containerWidth - mapWidth) / 2;
                    maxX = minX;
                    mapX = minX; // 强制居中
                } else {
                    // 地图宽度大于容器宽度时，允许拖动
                    minX = containerWidth - mapWidth; // 负数，允许向左拖动
                    maxX = 0; // 正数，允许向右拖动
                    mapX = Math.max(minX, Math.min(maxX, mapX));
                }
                
                if (mapHeight <= containerHeight) {
                    // 地图高度小于等于容器高度时，垂直居中
                    minY = (containerHeight - mapHeight) / 2;
                    maxY = minY;
                    mapY = minY; // 强制居中
                } else {
                    // 地图高度大于容器高度时，允许拖动
                    minY = containerHeight - mapHeight;
                    maxY = 0;
                    mapY = Math.max(minY, Math.min(maxY, mapY));
                }
                
                map.style.left = mapX + 'px';
                map.style.top = mapY + 'px';
                map.style.transform = 'scale(' + scale + ')';
                map.style.transformOrigin = '0 0';
                updateZoomLevel();
            }
            
            function updateZoomLevel() {
                document.getElementById('zoomLevel').innerText = Math.round(scale * 100) + '%';
            }
            
            function zoomIn() {
                if (scale < 3) {
                    scale += 0.2;
                    updateMapPosition();
                }
            }
            
            function zoomOut() {
                if (scale > 0.3) {
                    scale -= 0.2;
                    updateMapPosition();
                }
            }
            
            function resetZoom() {
                scale = 1;
                updateMapPosition();
            }
            
            // 鼠标滚轮缩放
            mapContainer.addEventListener('wheel', function(e) {
                e.preventDefault();
                var delta = e.deltaY > 0 ? -0.1 : 0.1;
                var newScale = scale + delta;
                
                if (newScale >= 0.3 && newScale <= 3) {
                    // 获取鼠标在地图上的位置
                    var rect = map.getBoundingClientRect();
                    var mouseX = e.clientX - rect.left;
                    var mouseY = e.clientY - rect.top;
                    
                    // 计算缩放前鼠标在地图上的相对位置
                    var relativeX = mouseX / scale;
                    var relativeY = mouseY / scale;
                    
                    scale = newScale;
                    
                    // 调整地图位置，使鼠标位置保持不变
                    mapX -= (relativeX * scale - mouseX);
                    mapY -= (relativeY * scale - mouseY);
                    
                    updateMapPosition();
                }
            });
            
            // 拖动事件
            mapContainer.addEventListener('mousedown', function(e) {
                if (e.target.classList.contains('outpost')) return;
                if (e.target.closest('.create-modal, .modal-overlay, .topbar')) return;
                
                isDragging = true;
                hasMoved = false;
                startX = e.clientX - mapX;
                startY = e.clientY - mapY;
                e.preventDefault();
            });
            
            document.addEventListener('mousemove', function(e) {
                if (!isDragging) return;
                hasMoved = true;
                mapX = e.clientX - startX;
                mapY = e.clientY - startY;
                updateMapPosition();
            });
            
            document.addEventListener('mouseup', function() {
                isDragging = false;
                // 延迟重置hasMoved，避免click事件立即触发
                setTimeout(function() {
                    hasMoved = false;
                }, 10);
            });
            
            // 地图点击功能已移除，房间创建改为在据点弹窗中进行
            
            function openCreateModal() {
                document.getElementById('modalOverlay').style.display = 'block';
                document.getElementById('createModal').style.display = 'block';
            }
            
            function closeCreateModal() {
                document.getElementById('modalOverlay').style.display = 'none';
                document.getElementById('createModal').style.display = 'none';
                document.getElementById('createForm').reset();
            }
            
            // 据点创建房间表单提交
            document.getElementById('fortressCreateForm').addEventListener('submit', function(e) {
                e.preventDefault();
                var formData = new FormData(e.target);
                
                fetch('/create_fortress_room', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.text())
                .then(data => {
                    if (data === 'success') {
                        // 重新加载据点房间列表
                        const fortressId = document.getElementById('fortressId').value;
                        loadFortressRooms(fortressId);
                        // 清空表单
                        e.target.reset();
                        // 显示成功提示
                        const roomList = document.getElementById('fortressRoomList');
                        const successMsg = document.createElement('div');
                        successMsg.style.cssText = 'color: #10b981; text-align: center; padding: 10px; margin-bottom: 10px; font-size: 12px;';
                        successMsg.textContent = '✅ 房间创建成功！';
                        roomList.parentNode.insertBefore(successMsg, roomList);
                        setTimeout(() => successMsg.remove(), 3000);
                    } else {
                        alert('创建房间失败：' + data);
                    }
                })
                .catch(error => {
                    console.error('创建房间失败:', error);
                    alert('创建房间失败，请重试');
                });
            });
            
            document.getElementById('createForm').addEventListener('submit', function(e) {
                e.preventDefault();
                var formData = new FormData(e.target);
                
                fetch('/create_with_location', {
                    method: 'POST',
                    body: formData
                }).then(function(response) {
                    if (response.ok) {
                        closeCreateModal();
                        window.location.reload();
                    }
                });
            });
            
            // 渲染房间
            function renderOutposts() {
                var mapElement = document.getElementById('map');
                
                rooms.forEach(function(room) {
                    if (room.x && room.y) {
                        var outpost = document.createElement('div');
                        outpost.className = 'outpost';
                        outpost.dataset.roomId = room.id;
                        outpost.style.left = (room.x / 2000 * 100) + '%';
                        outpost.style.top = (room.y / 2000 * 100) + '%';
                        outpost.onclick = function() {
                            showRoomInfoModal(room);
                        };
                        
                        outpost.innerHTML = '<div class="outpost-icon">🏰</div><div class="outpost-tooltip"><div class="outpost-name">' + room.name + '</div><div class="outpost-owner">房主：' + room.owner + '</div></div>';
                        
                        // 创建白色环状光环
                        var whiteRing = document.createElement('div');
                        whiteRing.className = 'white-ring';
                        
                        // 根据在线人数决定光环大小
                        if (room.online_count >= 6) {
                            whiteRing.classList.add('ring-large');
                        } else if (room.online_count >= 3) {
                            whiteRing.classList.add('ring-medium');
                        } else {
                            whiteRing.classList.add('ring-small');
                        }
                        
                        whiteRing.style.left = (room.x / 2000 * 100) + '%';
                        whiteRing.style.top = (room.y / 2000 * 100) + '%';
                        
                        // 创建多层立体光环
                        var ringOuter = document.createElement('div');
                        ringOuter.className = 'ring-layer ring-outer';
                        ringOuter.style.left = '50%';
                        ringOuter.style.top = '50%';
                        ringOuter.style.transform = 'translate(-50%, -50%)';
                        
                        var ringMiddle = document.createElement('div');
                        ringMiddle.className = 'ring-layer ring-middle';
                        ringMiddle.style.left = '50%';
                        ringMiddle.style.top = '50%';
                        ringMiddle.style.transform = 'translate(-50%, -50%)';
                        
                        var ringInner = document.createElement('div');
                        ringInner.className = 'ring-layer ring-inner';
                        ringInner.style.left = '50%';
                        ringInner.style.top = '50%';
                        ringInner.style.transform = 'translate(-50%, -50%)';
                        
                        // 组装多层光环
                        whiteRing.appendChild(ringOuter);
                        whiteRing.appendChild(ringMiddle);
                        whiteRing.appendChild(ringInner);
                        
                        mapElement.appendChild(outpost);
                        mapElement.appendChild(whiteRing);
                    }
                });
            }
            
            // 渲染据点系统
            function renderFortresses() {
                var mapElement = document.getElementById('map');
                
                fortresses.forEach(function(fortress) {
                    // 直接使用数据库中的像素坐标和半径
                    var x = fortress.x;
                    var y = fortress.y;
                    var radius = fortress.radius;
                    
                    console.log(`渲染据点 ${fortress.name}: 坐标(${x}px, ${y}px), 半径${radius}px`);
                    
                    // 创建据点呼吸光环
                    var fortressRing = document.createElement('div');
                    fortressRing.className = 'fortress-ring';
                    fortressRing.style.position = 'absolute';
                    fortressRing.style.left = x + 'px';
                    fortressRing.style.top = y + 'px';
                    fortressRing.style.transform = 'translate(-50%, -50%)';
                    fortressRing.style.pointerEvents = 'none';
                    fortressRing.style.zIndex = '2';
                    
                    // 根据据点大小决定光环类型
                    if (radius >= 500) {
                        fortressRing.classList.add('fortress-ring-large');
                    } else if (radius >= 200) {
                        fortressRing.classList.add('fortress-ring-medium');
                    } else {
                        fortressRing.classList.add('fortress-ring-small');
                    }
                    
                    // 创建多层立体光环
                    var ringOuter = document.createElement('div');
                    ringOuter.className = 'fortress-ring-layer fortress-ring-outer';
                    ringOuter.style.left = '50%';
                    ringOuter.style.top = '50%';
                    ringOuter.style.transform = 'translate(-50%, -50%)';
                    ringOuter.style.borderColor = 'rgba(255, 255, 255, 0.6)';
                    ringOuter.style.boxShadow = '0 0 20px rgba(255, 255, 255, 0.8), 0 0 40px rgba(255, 255, 255, 0.4)';
                    
                    var ringMiddle = document.createElement('div');
                    ringMiddle.className = 'fortress-ring-layer fortress-ring-middle';
                    ringMiddle.style.left = '50%';
                    ringMiddle.style.top = '50%';
                    ringMiddle.style.transform = 'translate(-50%, -50%)';
                    ringMiddle.style.borderColor = '#ffffff';
                    ringMiddle.style.boxShadow = '0 0 15px rgba(255, 255, 255, 1), 0 0 30px rgba(255, 255, 255, 0.8)';
                    
                    var ringInner = document.createElement('div');
                    ringInner.className = 'fortress-ring-layer fortress-ring-inner';
                    ringInner.style.left = '50%';
                    ringInner.style.top = '50%';
                    ringInner.style.transform = 'translate(-50%, -50%)';
                    ringInner.style.borderColor = 'rgba(255, 255, 255, 0.9)';
                    ringInner.style.boxShadow = '0 0 10px rgba(255, 255, 255, 1), 0 0 20px rgba(255, 255, 255, 0.8)';
                    
                    // 组装多层光环
                    fortressRing.appendChild(ringOuter);
                    fortressRing.appendChild(ringMiddle);
                    fortressRing.appendChild(ringInner);
                    
                    // 创建据点中心点
                    var fortressCenter = document.createElement('div');
                    fortressCenter.className = 'fortress-center';
                    fortressCenter.style.position = 'absolute';
                    fortressCenter.style.left = x + 'px';
                    fortressCenter.style.top = y + 'px';
                    fortressCenter.style.transform = 'translate(-50%, -50%)';
                    fortressCenter.style.width = '20px';
                    fortressCenter.style.height = '20px';
                    fortressCenter.style.borderRadius = '50%';
                    fortressCenter.style.background = fortress.color;
                    fortressCenter.style.border = '3px solid #fff';
                    fortressCenter.style.cursor = 'pointer';
                    fortressCenter.style.zIndex = '5';
                    fortressCenter.onclick = function() {
                        showFortressInfo(fortress);
                    };
                    
                    // 创建据点标签 - 使用像素坐标
                    var fortressLabel = document.createElement('div');
                    fortressLabel.className = 'fortress-label';
                    fortressLabel.style.position = 'absolute';
                    fortressLabel.style.left = x + 'px';
                    fortressLabel.style.top = (y + radius + 20) + 'px'; // 像素偏移
                    fortressLabel.style.transform = 'translateX(-50%)';
                    fortressLabel.style.color = fortress.color;
                    fortressLabel.style.fontSize = '12px';
                    fortressLabel.style.fontWeight = '700';
                    fortressLabel.style.textShadow = '0 0 5px rgba(0,0,0,0.8)';
                    fortressLabel.style.pointerEvents = 'none';
                    fortressLabel.style.zIndex = '4';
                    fortressLabel.textContent = fortress.name;
                    
                    mapElement.appendChild(fortressRing);
                    mapElement.appendChild(fortressCenter);
                    mapElement.appendChild(fortressLabel);
                });
            }
            
            // 显示据点信息
            function showFortressInfo(fortress) {
                document.getElementById('roomInfoName').textContent = fortress.name;
                document.getElementById('roomInfoDetails').innerHTML = 
                    '<div>据点ID：' + fortress.id + '</div>' +
                    '<div>位置：(' + fortress.x + ', ' + fortress.y + ')</div>' +
                    '<div>半径：' + fortress.radius + '</div>' +
                    '<div>描述：' + (fortress.description || '无描述') + '</div>';
                
                // 设置创建房间表单的隐藏字段
                document.getElementById('fortressId').value = fortress.id;
                document.getElementById('fortressX').value = fortress.x;
                document.getElementById('fortressY').value = fortress.y;
                
                // 加载据点房间列表
                loadFortressRooms(fortress.id);
                
                document.getElementById('roomInfoOverlay').style.display = 'block';
                document.getElementById('roomInfoModal').style.display = 'block';
                
                // 启动据点弹窗粒子系统
                if (modalParticleSystem) {
                    setTimeout(() => {
                        modalParticleSystem.init();
                    }, 100);
                }
            }
            
            // 加载据点房间列表
            function loadFortressRooms(fortressId) {
                fetch('/api/fortress_rooms/' + fortressId)
                    .then(response => response.json())
                    .then(data => {
                        const roomList = document.getElementById('fortressRoomList');
                        roomList.innerHTML = '';
                        
                        if (data.rooms && data.rooms.length > 0) {
                            data.rooms.forEach(room => {
                                const roomItem = document.createElement('div');
                                roomItem.style.cssText = 'background: #111827; border: 1px solid #374151; border-radius: 6px; padding: 10px; margin-bottom: 8px; cursor: pointer; transition: all 0.2s ease;';
                                roomItem.innerHTML = 
                                    '<div style="color: #fff; font-weight: bold; font-size: 13px; margin-bottom: 4px;">🏠 ' + room.name + '</div>' +
                                    '<div style="color: #cbd5e1; font-size: 11px;">房主：' + room.owner + ' | 在线：' + (room.online_count || 0) + '人</div>';
                                
                                roomItem.onclick = function() {
                                    closeRoomInfoModal();
                                    window.location.href = '/room/' + room.id;
                                };
                                
                                roomItem.onmouseover = function() {
                                    this.style.background = '#374151';
                                    this.style.borderColor = '#2dd4bf';
                                };
                                
                                roomItem.onmouseout = function() {
                                    this.style.background = '#111827';
                                    this.style.borderColor = '#374151';
                                };
                                
                                roomList.appendChild(roomItem);
                            });
                        } else {
                            roomList.innerHTML = '<div style="color: #9ca3af; text-align: center; padding: 20px; font-size: 12px;">此据点暂无房间</div>';
                        }
                    })
                    .catch(error => {
                        console.error('加载据点房间失败:', error);
                        document.getElementById('fortressRoomList').innerHTML = '<div style="color: #ef4444; text-align: center; padding: 20px; font-size: 12px;">加载失败</div>';
                    });
            }
            
            // 房间信息弹窗函数
            function showRoomInfoModal(room) {
                document.getElementById('roomInfoName').textContent = room.name;
                document.getElementById('roomInfoDetails').innerHTML = 
                    '<div>房主：' + room.owner + '</div>' +
                    '<div>房间ID：' + room.id + '</div>' +
                    '<div>位置：(' + room.x + ', ' + room.y + ')</div>';
                
                document.getElementById('joinRoomBtn').onclick = function() {
                    window.location.href = '/room/' + room.id;
                };
                
                document.getElementById('roomInfoOverlay').style.display = 'block';
                document.getElementById('roomInfoModal').style.display = 'block';
            }
            
            function closeRoomInfoModal() {
                document.getElementById('roomInfoOverlay').style.display = 'none';
                document.getElementById('roomInfoModal').style.display = 'none';
                
                // 停止据点弹窗粒子系统
                if (modalParticleSystem) {
                    modalParticleSystem.stop();
                }
            }
            
            // 我的房间弹窗函数
            function showMyOutpostsModal() {
                var outpostList = document.getElementById('myOutpostsList');
                outpostList.innerHTML = '';
                
                if (userRooms.length === 0) {
                    outpostList.innerHTML = '<div style="color:#9ca3af;text-align:center;padding:20px">暂无房间，点击地图创建您的第一个房间</div>';
                } else {
                    userRooms.forEach(function(room) {
                        var outpostItem = document.createElement('div');
                        outpostItem.className = 'outpost-item';
                        outpostItem.onclick = function() {
                            closeMyOutpostsModal();
                            locateToOutpost(room);
                        };
                        
                        outpostItem.innerHTML = 
                            '<div class="outpost-item-name">🏰 ' + room.name + '</div>' +
                            '<div class="outpost-item-details">房主：' + room.owner + ' | 位置：(' + room.x + ', ' + room.y + ')</div>';
                        
                        outpostList.appendChild(outpostItem);
                    });
                }
                
                document.getElementById('myOutpostsOverlay').style.display = 'block';
                document.getElementById('myOutpostsModal').style.display = 'block';
            }
            
            function closeMyOutpostsModal() {
                document.getElementById('myOutpostsOverlay').style.display = 'none';
                document.getElementById('myOutpostsModal').style.display = 'none';
            }
            
            // 定位到指定房间
            function locateToOutpost(room) {
                if (room.x && room.y) {
                    // 计算房间在地图上的位置
                    var targetX = -(room.x / 2000 * 4081 * scale) + window.innerWidth / 2;
                    var targetY = -(room.y / 2000 * 5488 * scale) + window.innerHeight / 2;
                    
                    // 应用边界限制
                    var mapWidth = 4081 * scale;
                    var mapHeight = 5488 * scale;
                    var containerWidth = window.innerWidth;
                    var containerHeight = window.innerHeight;
                    
                    var minX, minY, maxX, maxY;
                    
                    if (mapWidth <= containerWidth) {
                        minX = (containerWidth - mapWidth) / 2;
                        maxX = minX;
                        targetX = minX;
                    } else {
                        minX = containerWidth - mapWidth;
                        maxX = 0;
                        targetX = Math.max(minX, Math.min(maxX, targetX));
                    }
                    
                    if (mapHeight <= containerHeight) {
                        minY = (containerHeight - mapHeight) / 2;
                        maxY = minY;
                        targetY = minY;
                    } else {
                        minY = containerHeight - mapHeight;
                        maxY = 0;
                        targetY = Math.max(minY, Math.min(maxY, targetY));
                    }
                    
                    // 平滑移动到目标位置
                    mapX = targetX;
                    mapY = targetY;
                    updateMapPosition();
                    saveMapState();
                    
                    // 高亮显示目标房间
                    highlightOutpost(room.id);
                }
            }
            
            // 高亮显示房间
            function highlightOutpost(roomId) {
                var outposts = document.querySelectorAll('.outpost');
                outposts.forEach(function(outpost) {
                    if (outpost.dataset.roomId == roomId) {
                        outpost.style.boxShadow = '0 0 30px #2dd4bf, 0 0 60px #2dd4bf';
                        setTimeout(function() {
                            outpost.style.boxShadow = '';
                        }, 2000);
                    }
                });
            }
            
            // 侧边栏控制函数
            function toggleSidebar() {
                var sidebar = document.getElementById('tacticalSidebar');
                var icon = document.getElementById('sidebarToggleIcon');
                
                if (sidebar.classList.contains('sidebar-collapsed')) {
                    // 展开侧边栏
                    sidebar.classList.remove('sidebar-collapsed');
                    sidebar.classList.add('sidebar-expanded');
                    icon.textContent = '✕';
                    renderSidebarOutposts();
                } else {
                    // 收起侧边栏
                    sidebar.classList.remove('sidebar-expanded');
                    sidebar.classList.add('sidebar-collapsed');
                    icon.textContent = '⚔️';
                }
            }
            
            // 渲染侧边栏房间列表
            function renderSidebarOutposts() {
                var outpostList = document.getElementById('sidebarOutpostList');
                outpostList.innerHTML = '';
                
                if (rooms.length === 0) {
                    outpostList.innerHTML = '<div style="color:#9ca3af;text-align:center;padding:10px;font-size:11px">暂无房间</div>';
                } else {
                    // 按在线人数排序
                    var sortedRooms = rooms.slice().sort(function(a, b) {
                        return (b.online_count || 0) - (a.online_count || 0);
                    });
                    
                    sortedRooms.forEach(function(room) {
                        if (room.x && room.y) {
                            var outpostItem = document.createElement('div');
                            outpostItem.className = 'sidebar-outpost-item';
                            outpostItem.onclick = function() {
                                locateToOutpost(room);
                            };
                            
                            var onlineCount = room.online_count || 0;
                            var statusIcon = onlineCount >= 6 ? '🔥' : onlineCount >= 2 ? '⚡' : '💤';
                            var statusColor = onlineCount >= 6 ? '#ef4444' : onlineCount >= 2 ? '#3b82f6' : '#2dd4bf';
                            
                            outpostItem.innerHTML = 
                                '<div class="sidebar-outpost-name">' + statusIcon + ' ' + room.name + '</div>' +
                                '<div class="sidebar-outpost-info">房主：' + room.owner + ' | 在线：' + onlineCount + '人</div>';
                            
                            outpostList.appendChild(outpostItem);
                        }
                    });
                }
            }
            
            // 据点弹窗粒子系统 - 参照房间页面实现
            var modalParticleSystem = null;
            
            class ModalParticleSystem {
                constructor() {
                    this.canvas = document.getElementById('modalParticleCanvas');
                    this.ctx = this.canvas.getContext('2d');
                    this.particles = [];
                    this.mouseX = -1000;
                    this.mouseY = -1000;
                    this.config = {
                        particleSize: 2,
                        particleMargin: 2,
                        repulsionRadius: 80,
                        repulsionForce: 1.0,
                        friction: 0.15,
                        returnSpeed: 0.02,
                        maxDisplayRatio: 0.8,
                        samplingStep: 5,
                        mobileRepulsionRadius: 60
                    };
                    this.isActive = false;
                    this.modalRect = null;
                }
                
                init() {
                    if (!this.canvas) return;
                    
                    this.resizeCanvas();
                    this.createPatternParticles();
                    this.isActive = true;
                    this.animate();
                    
                    // 添加鼠标事件监听
                    document.addEventListener('mousemove', (e) => {
                        if (this.isActive) {
                            this.updateMousePosition(e);
                        }
                    });
                    
                    window.addEventListener('resize', () => {
                        this.resizeCanvas();
                    });
                }
                
                updateMousePosition(e) {
                    const modal = document.getElementById('roomInfoModal');
                    if (modal && modal.style.display === 'block') {
                        this.modalRect = modal.getBoundingClientRect();
                        this.mouseX = e.clientX - this.modalRect.left;
                        this.mouseY = e.clientY - this.modalRect.top;
                    }
                }
                
                resizeCanvas() {
                    const modal = document.getElementById('roomInfoModal');
                    if (modal && modal.style.display === 'block') {
                        this.canvas.width = modal.offsetWidth;
                        this.canvas.height = modal.offsetHeight;
                        this.modalRect = modal.getBoundingClientRect();
                    }
                }
                
                createPatternParticles() {
                    this.particles = [];
                    const canvasWidth = this.canvas.width;
                    const canvasHeight = this.canvas.height;
                    const maxDisplayWidth = canvasWidth * this.config.maxDisplayRatio;
                    const maxDisplayHeight = canvasHeight * this.config.maxDisplayRatio;
                    
                    // 加载Yan.png图片并创建粒子
                    this.loadImageAndCreateParticles('/static/images/img/Yan.png');
                }
                
                loadImageAndCreateParticles(imageSrc) {
                    console.log('开始加载图片并创建粒子...');
                    const img = new Image();
                    img.src = imageSrc;
                    console.log('图片路径:', img.src);
                    
                    img.onload = () => {
                        console.log('图片加载成功，图片尺寸:', img.width, 'x', img.height);
                        console.log('清空现有粒子并创建新粒子...');
                        this.particles = []; // 清空现有粒子
                        this.createParticlesFromImage(img);
                        console.log(`从图片创建了 ${this.particles.length} 个粒子`);
                    };
                    
                    img.onerror = (error) => {
                        console.log('图片加载失败，错误:', error);
                        console.log('创建备用图案粒子');
                        this.createFallbackPattern();
                    };
                }
                
                createParticlesFromImage(img) {
                    const canvasWidth = this.canvas.width;
                    const canvasHeight = this.canvas.height;
                    const maxDisplayWidth = canvasWidth * this.config.maxDisplayRatio;
                    const maxDisplayHeight = canvasHeight * this.config.maxDisplayRatio;
                    
                    const tempCanvas = document.createElement('canvas');
                    const tempCtx = tempCanvas.getContext('2d');
                    
                    let width = img.width;
                    let height = img.height;
                    console.log('原始图片尺寸:', width, 'x', height);
                    
                    if (width > maxDisplayWidth || height > maxDisplayHeight) {
                        const ratio = Math.min(maxDisplayWidth / width, maxDisplayHeight / height);
                        width *= ratio;
                        height *= ratio;
                        console.log('调整后尺寸:', width, 'x', height, '比例:', ratio);
                    }
                    
                    tempCanvas.width = width;
                    tempCanvas.height = height;
                    tempCtx.drawImage(img, 0, 0, width, height);
                    
                    const imgData = tempCtx.getImageData(0, 0, width, height);
                    console.log('获取图像数据，尺寸:', imgData.width, 'x', imgData.height);
                    
                    const offsetX = (canvasWidth - width) / 2;
                    const offsetY = (canvasHeight - height) / 2;
                    console.log('偏移量:', offsetX, offsetY);
                    
                    let particleCount = 0;
                    for (let y = 0; y < height; y += this.config.samplingStep) {
                        for (let x = 0; x < width; x += this.config.samplingStep) {
                            const alpha = imgData.data[(y * width + x) * 4 + 3];
                            if (alpha > 64) {
                                const brightness = this.getPixelBrightness(imgData, x, y);
                                const particle = new ModalParticle(
                                    x + offsetX,
                                    y + offsetY,
                                    this.config,
                                    brightness > 128 ? 'light' : 'dark'
                                );
                                this.particles.push(particle);
                                particleCount++;
                            }
                        }
                    }
                    console.log(`从图片创建了 ${particleCount} 个粒子`);
                }
                
                createFallbackPattern() {
                    const canvasWidth = this.canvas.width;
                    const canvasHeight = this.canvas.height;
                    const centerX = canvasWidth / 2;
                    const centerY = canvasHeight / 2;
                    const maxRadius = Math.min(centerX, centerY) * 0.9;
                    
                    // 创建多层圆形图案
                    for (let layer = 0; layer < 5; layer++) {
                        const layerRadius = maxRadius * (0.2 + layer * 0.15);
                        const particleCount = 20 + layer * 10;
                        
                        for (let i = 0; i < particleCount; i++) {
                            const angle = (i / particleCount) * Math.PI * 2;
                            const radiusVariation = layerRadius * (0.8 + Math.random() * 0.4);
                            const x = centerX + Math.cos(angle) * radiusVariation;
                            const y = centerY + Math.sin(angle) * radiusVariation;
                            const colorType = layer % 2 === 0 ? 'light' : 'dark';
                            this.particles.push(new ModalParticle(x, y, this.config, colorType));
                        }
                    }
                }
                
                getPixelBrightness(imgData, x, y) {
                    const i = (y * imgData.width + x) * 4;
                    return (imgData.data[i] + imgData.data[i + 1] + imgData.data[i + 2]) / 3;
                }
                
                animate() {
                    if (!this.isActive) return;
                    
                    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                    
                    this.particles.forEach(particle => {
                        particle.update(this.mouseX, this.mouseY, this.canvas.width, this.canvas.height);
                        particle.draw(this.ctx);
                    });
                    
                    requestAnimationFrame(() => this.animate());
                }
                
                start() {
                    this.isActive = true;
                    this.resizeCanvas();
                    this.animate();
                }
                
                stop() {
                    this.isActive = false;
                    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                }
            }
            
            class ModalParticle {
                constructor(x, y, config, colorType) {
                    this.x = x;
                    this.y = y;
                    this.vx = (Math.random() - 0.5) * 0.5;
                    this.vy = (Math.random() - 0.5) * 0.5;
                    this.config = config;
                    this.colorType = colorType;
                    this.opacity = Math.random() * 0.5 + 0.3;
                    this.originalX = x;
                    this.originalY = y;
                }
                
                update(mouseX, mouseY, canvasWidth, canvasHeight) {
                    // 鼠标排斥效果
                    const dx = this.x - mouseX;
                    const dy = this.y - mouseY;
                    const distance = Math.sqrt(dx * dx + dy * dy);
                    
                    if (distance < this.config.repulsionRadius) {
                        const force = (1 - distance / this.config.repulsionRadius) * this.config.repulsionForce;
                        const angle = Math.atan2(dy, dx);
                        this.vx += Math.cos(angle) * force;
                        this.vy += Math.sin(angle) * force;
                    }
                    
                    // 添加向原位置的恢复力
                    this.vx += (this.originalX - this.x) * this.config.returnSpeed;
                    this.vy += (this.originalY - this.y) * this.config.returnSpeed;
                    
                    // 应用摩擦力
                    this.vx *= (1 - this.config.friction);
                    this.vy *= (1 - this.config.friction);
                    
                    // 更新位置
                    this.x += this.vx;
                    this.y += this.vy;
                    
                    // 边界检测
                    if (this.x < 0 || this.x > canvasWidth) {
                        this.vx *= -0.8;
                        this.x = Math.max(0, Math.min(canvasWidth, this.x));
                    }
                    if (this.y < 0 || this.y > canvasHeight) {
                        this.vy *= -0.8;
                        this.y = Math.max(0, Math.min(canvasHeight, this.y));
                    }
                }
                
                draw(ctx) {
                    const color = this.colorType === 'light' 
                        ? `rgba(45, 212, 191, ${this.opacity})`
                        : `rgba(139, 92, 246, ${this.opacity})`;
                    
                    ctx.fillStyle = color;
                    ctx.beginPath();
                    ctx.arc(this.x, this.y, this.config.particleSize, 0, Math.PI * 2);
                    ctx.fill();
                }
            }
            
            // 初始化
            window.addEventListener('load', function() {
                centerMap();
                
                // 检查据点数据
                console.log('据点数量:', fortresses.length);
                if (fortresses.length > 0) {
                    console.log('第一个据点:', fortresses[0]);
                }
                
                renderFortresses(); // 渲染据点系统
                renderOutposts(); // 渲染房间
                
                // 初始化据点弹窗粒子系统
                modalParticleSystem = new ModalParticleSystem();
            });
            
            window.addEventListener('resize', centerMap);
        </script>
    </body>
    </html>
    '''
    return html

@main_bp.route('/create_fortress_room', methods=['POST'])
def create_fortress_room():
    if "user" not in session: 
        return "error", 401
    
    name = request.form['name']
    fortress_id = request.form['fortress_id']
    x = request.form['x']
    y = request.form['y']
    
    room_id, error = create_room_with_fortress(name, session['user'], x, y, fortress_id)
    if error: 
        return error, 400
    
    return "success", 200

@main_bp.route('/api/fortress_rooms/<int:fortress_id>')
def get_fortress_rooms(fortress_id):
    print(f"DEBUG: Getting rooms for fortress_id = {fortress_id}")
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 查询指定据点的房间
        cursor.execute("""
            SELECT r.id, r.name, r.owner, r.x, r.y, r.fortress_id
            FROM rooms r 
            WHERE r.fortress_id = %s 
            ORDER BY r.id DESC
        """, (fortress_id,))
        
        rooms = []
        rows = cursor.fetchall()
        print(f"DEBUG: Found {len(rows)} rooms for fortress {fortress_id}")
        print(f"DEBUG: Raw query results: {rows}")
        
        for row in rows:
            rooms.append({
                'id': row[0],
                'name': row[1],
                'owner': row[2],
                'x': row[3],
                'y': row[4],
                'fortress_id': row[5],
                'online_count': get_real_online_count(row[0])  #  Get real online count
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({'rooms': rooms})
        
    except Exception as e:
        print(f"获取据点房间失败: {e}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/create_with_location', methods=['POST'])
def create_with_location():
    if "user" not in session: 
        return "error", 401
    
    name = request.form['name']
    x = float(request.form['x'])
    y = float(request.form['y'])
    
    room_id, error = create_room(name, session['user'], x, y)
    if error: 
        return "error", 400
    
    return "success", 200
