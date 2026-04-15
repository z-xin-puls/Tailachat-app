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
