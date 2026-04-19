# 管理员路由
from flask import Blueprint, request, redirect, render_template, session, jsonify
from models.database import get_db_connection
from models.user import get_user_profiles, get_user_role
from models.room import get_all_rooms
from utils.decorators import admin_required
from utils.helpers import html_escape

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@admin_required
def admin_dashboard():
    """管理员面板主页"""
    # 获取统计信息
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 用户统计
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        # 房间统计
        cursor.execute("SELECT COUNT(*) FROM rooms")
        total_rooms = cursor.fetchone()[0]
        
        # 据点统计
        cursor.execute("SELECT COUNT(*) FROM fortresses")
        total_fortresses = cursor.fetchone()[0]
        
        conn.close()
    except Exception as e:
        print(f"获取统计信息失败: {e}")
        total_users = 0
        admin_count = 0
        total_rooms = 0
        total_fortresses = 0
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         admin_count=admin_count,
                         total_rooms=total_rooms,
                         total_fortresses=total_fortresses)

@admin_bp.route('/admin/users')
@admin_required
def admin_users():
    """用户管理页面"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username, nickname, avatar, role FROM users ORDER BY username")
        users = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"获取用户列表失败: {e}")
        users = []
    
    return render_template('admin/users.html', users=users)

@admin_bp.route('/admin/api/users', methods=['GET'])
@admin_required
def api_users():
    """获取用户列表API"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username, nickname, avatar, role FROM users ORDER BY username")
        users = cursor.fetchall()
        conn.close()
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        print(f"获取用户列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/user/<username>/role', methods=['PUT'])
@admin_required
def update_user_role(username):
    """更新用户角色"""
    try:
        data = request.get_json()
        new_role = data.get('role')
        
        if new_role not in ['user', 'admin']:
            return jsonify({'success': False, 'error': '无效的角色'})
        
        # 不允许修改自己的角色
        if username == session['user']:
            return jsonify({'success': False, 'error': '不能修改自己的角色'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = %s WHERE username = %s", (new_role, username))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"更新用户角色失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/user/<username>/delete', methods=['DELETE'])
@admin_required
def delete_user(username):
    """删除用户"""
    try:
        # 不允许删除自己
        if username == session['user']:
            return jsonify({'success': False, 'error': '不能删除自己'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"删除用户失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/rooms')
@admin_required
def admin_rooms():
    """房间管理页面"""
    try:
        rooms = get_all_rooms()
    except Exception as e:
        print(f"获取房间列表失败: {e}")
        rooms = []
    
    return render_template('admin/rooms.html', rooms=rooms)

@admin_bp.route('/admin/api/room/<int:room_id>/delete', methods=['DELETE'])
@admin_required
def delete_room(room_id):
    """删除房间"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rooms WHERE id = %s", (room_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"删除房间失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/fortresses')
@admin_required
def admin_fortresses():
    """据点管理页面"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, x, y, radius, color, description, image FROM fortresses ORDER BY id")
        fortresses = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"获取据点列表失败: {e}")
        fortresses = []
    
    return render_template('admin/fortresses.html', fortresses=fortresses)

@admin_bp.route('/admin/api/fortress', methods=['POST'])
@admin_required
def create_fortress():
    """创建据点"""
    try:
        data = request.get_json()
        name = data.get('name')
        x = data.get('x')
        y = data.get('y')
        radius = data.get('radius')
        color = data.get('color')
        description = data.get('description', '')
        image = data.get('image', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO fortresses (name, x, y, radius, color, description, image)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (name, x, y, radius, color, description, image))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"创建据点失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/fortress/<int:fortress_id>', methods=['PUT'])
@admin_required
def update_fortress(fortress_id):
    """更新据点"""
    try:
        data = request.get_json()
        name = data.get('name')
        x = data.get('x')
        y = data.get('y')
        radius = data.get('radius')
        color = data.get('color')
        description = data.get('description', '')
        image = data.get('image', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE fortresses SET name = %s, x = %s, y = %s, radius = %s, color = %s, description = %s, image = %s
            WHERE id = %s
        """, (name, x, y, radius, color, description, image, fortress_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"更新据点失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/fortress/<int:fortress_id>/delete', methods=['DELETE'])
@admin_required
def delete_fortress(fortress_id):
    """删除据点"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fortresses WHERE id = %s", (fortress_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"删除据点失败: {e}")
        return jsonify({'success': False, 'error': str(e)})
