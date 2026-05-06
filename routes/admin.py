# 管理员路由
from flask import Blueprint, request, redirect, render_template, session, jsonify
from models.database import get_db_connection
from models.user import get_user_profiles, get_user_role
from models.room import get_all_rooms
from models.analytics import get_dashboard_stats, get_user_growth_trend, get_room_creation_trend, get_hourly_activity_analysis, get_activity_statistics, get_user_activity_heatmap_data
from models.charts import create_dashboard_grid, create_user_role_pie_chart, create_activity_statistics_chart, create_user_activity_heatmap
from utils.decorators import admin_required
from utils.helpers import html_escape

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@admin_required
def admin_dashboard():
    """管理员面板主页"""
    # 获取实时在线用户数
    online_users = 0
    active_rooms = 0
    try:
        from app import get_realtime_stats
        stats = get_realtime_stats()
        online_users = stats['online_users']
        active_rooms = stats['active_rooms']
    except Exception as e:
        print(f"获取实时统计失败: {e}")
        online_users = 0
        active_rooms = 0
    
    # 获取统计信息
    stats = get_dashboard_stats(online_users=online_users, active_rooms=active_rooms)
    
    # 获取图表数据
    user_growth_data = get_user_growth_trend(days=7)
    room_creation_data = get_room_creation_trend(days=7)
    hourly_activity_data = get_hourly_activity_analysis(days=7)
    activity_stats = get_activity_statistics(days=7)
    heatmap_data = get_user_activity_heatmap_data(days=30)
    
    # 生成图表
    dashboard_charts = create_dashboard_grid(user_growth_data, room_creation_data, hourly_activity_data)
    role_pie_chart = create_user_role_pie_chart(stats['admin_count'], stats['total_users'] - stats['admin_count'])
    activity_chart = create_activity_statistics_chart(activity_stats)
    heatmap_chart = create_user_activity_heatmap(heatmap_data)
    
    # 渲染图表为HTML
    user_growth_html = dashboard_charts.get('user_growth', {}).render_embed() if dashboard_charts.get('user_growth') else ""
    room_creation_html = dashboard_charts.get('room_creation', {}).render_embed() if dashboard_charts.get('room_creation') else ""
    hourly_activity_html = dashboard_charts.get('hourly_activity', {}).render_embed() if dashboard_charts.get('hourly_activity') else ""
    pie_html = role_pie_chart.render_embed() if role_pie_chart else ""
    activity_html = activity_chart.render_embed() if activity_chart else ""
    heatmap_html = heatmap_chart.render_embed() if heatmap_chart else ""
    
    return render_template('admin/dashboard.html',
                         total_users=stats['total_users'],
                         admin_count=stats['admin_count'],
                         total_rooms=stats['total_rooms'],
                         total_fortresses=stats['total_fortresses'],
                         online_users=stats['online_users'],
                         today_active_users=stats['today_active_users'],
                         active_rooms=stats['active_rooms'],
                         today_created_rooms=stats['today_created_rooms'],
                         user_growth_html=user_growth_html,
                         room_creation_html=room_creation_html,
                         hourly_activity_html=hourly_activity_html,
                         role_pie_html=pie_html,
                         activity_chart_html=activity_html,
                         heatmap_html=heatmap_html)

@admin_bp.route('/admin/users')
@admin_required
def admin_users():
    """用户管理页面"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, nickname, avatar, role, banned, ban_reason, ban_time FROM users ORDER BY username")
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

@admin_bp.route('/admin/api/user/<username>/reset_password', methods=['POST'])
@admin_required
def reset_user_password(username):
    """重置用户密码为123456"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查用户是否存在
        cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '用户不存在'})

        # 重置密码为123456
        cursor.execute("UPDATE users SET password = %s WHERE username = %s", ('123456', username))
        conn.commit()
        conn.close()

        return jsonify({'success': True})
    except Exception as e:
        print(f"重置密码失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/user/<username>/ban', methods=['POST'])
@admin_required
def ban_user(username):
    """封禁用户"""
    try:
        data = request.get_json()
        reason = data.get('reason', '').strip()

        if not reason:
            return jsonify({'success': False, 'error': '封禁原因不能为空'})

        # 不允许封禁自己
        if username == session['user']:
            return jsonify({'success': False, 'error': '不能封禁自己'})

        # 不允许封禁管理员
        if get_user_role(username) == 'admin':
            return jsonify({'success': False, 'error': '不能封禁管理员'})

        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查用户是否存在
        cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '用户不存在'})

        # 封禁用户
        cursor.execute("""
            UPDATE users SET 
            banned = TRUE, 
            ban_reason = %s, 
            ban_time = NOW() 
            WHERE username = %s
        """, (reason, username))
        conn.commit()
        conn.close()

        return jsonify({'success': True})
    except Exception as e:
        print(f"封禁用户失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/user/<username>/unban', methods=['POST'])
@admin_required
def unban_user(username):
    """解封用户"""
    try:
        # 不允许解封自己（虽然自己不会被封禁）
        if username == session['user']:
            return jsonify({'success': False, 'error': '不能操作自己'})

        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查用户是否存在
        cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '用户不存在'})

        # 解封用户
        cursor.execute("""
            UPDATE users SET 
            banned = FALSE, 
            ban_reason = NULL, 
            ban_time = NULL 
            WHERE username = %s
        """, (username,))
        conn.commit()
        conn.close()

        return jsonify({'success': True})
    except Exception as e:
        print(f"解封用户失败: {e}")
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
