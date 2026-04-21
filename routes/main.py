# 主页和地图路由
from flask import Blueprint, request, redirect, render_template, session, jsonify
from models.database import get_db_connection
from models.user import get_user_profiles, get_user_role
from models.room import get_all_rooms, create_room, create_room_with_fortress
from utils.validators import validate_room_name
from utils.helpers import html_escape
from utils.logger import log_user_action
import json
import requests

main_bp = Blueprint('main', __name__)

def get_real_online_count(room_id):
    """Get real online user count by calling app.py's API endpoint"""
    try:
        from flask import request
        host = request.host_url.rstrip('/')
        res = requests.get(f'{host}/room-data/{room_id}', timeout=2)
        if res.status_code == 200:
            result = res.json()
            return result.get('count', 0)
        return 0
    except:
        return 0

@main_bp.route('/')
def index():
    if "user" not in session:
        return redirect("/login")

    prof = get_user_profiles([session["user"]]).get(session["user"]) or {}
    display_user = (prof.get("nickname") or session["user"])
    
    # 获取用户角色
    user_role = get_user_role(session['user'])

    rooms = get_all_rooms()

    # 为每个房间添加在线人数（移除HTTP请求以提升性能）
    for room in rooms:
        room['online_count'] = 0

    # 获取用户相关的房间（用户创建的或加入的）
    user_rooms = [room for room in rooms if room['owner'] == session['user']]

    # 获取据点信息
    fortress_list = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, x, y, radius, color, description, image FROM fortresses ORDER BY id")
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
                'description': fortress[6] if fortress[6] else '',
                'image': fortress[7] if fortress[7] else None
            }
            fortress_list.append(fortress_dict)

        conn.close()

    except Exception as e:
        print(f"获取据点数据失败: {e}")

    return render_template('main/index.html',
                         current_user=html_escape(display_user),
                         user_role=user_role,
                         rooms=json.dumps([{'id': r['id'], 'name': r['name'], 'owner': r['owner'], 'x': r['x'], 'y': r['y'], 'online_count': r['online_count']} for r in rooms]),
                         user_rooms=json.dumps([{'id': r['id'], 'name': r['name'], 'owner': r['owner'], 'x': r['x'], 'y': r['y'], 'online_count': r['online_count']} for r in user_rooms]),
                         fortresses=json.dumps(fortress_list))

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

    # 记录创建房间日志
    log_user_action(
        username=session['user'],
        action_type='create_room',
        action_detail={'room_id': room_id, 'room_name': name, 'fortress_id': fortress_id},
        ip=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )

    # 记录房间活动到room_activity表
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO room_activity (room_id, room_name, action, owner)
            VALUES (%s, %s, %s, %s)
        """, (room_id, name, 'create', session['user']))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"记录房间活动失败: {e}")

    return "success", 200

@main_bp.route('/api/fortress_rooms/<int:fortress_id>')
def get_fortress_rooms(fortress_id):
    try:
        conn = get_db_connection()
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

        for row in rows:
            rooms.append({
                'id': row[0],
                'name': row[1],
                'owner': row[2],
                'x': row[3],
                'y': row[4],
                'fortress_id': row[5],
                'online_count': 0  # 移除HTTP请求以提升性能
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

    # 记录创建房间日志
    log_user_action(
        username=session['user'],
        action_type='create_room',
        action_detail={'room_id': room_id, 'room_name': name, 'x': x, 'y': y},
        ip=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )

    return "success", 200
