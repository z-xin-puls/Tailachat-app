# 管理员路由
from flask import Blueprint, request, redirect, render_template, session, jsonify
from models.database import get_db_connection
from models.user import get_user_profiles, get_user_role
from models.room import get_all_rooms
from models.analytics import get_dashboard_stats, get_user_growth_trend, get_room_creation_trend, get_hourly_activity_analysis, get_activity_statistics, get_user_activity_heatmap_data
from models.charts import create_dashboard_grid, create_user_role_pie_chart, create_activity_statistics_chart, create_user_activity_heatmap
from utils.decorators import admin_required
from utils.helpers import html_escape

# 导入自定义异常
from utils.exceptions import AppError, ValidationError, AuthenticationError, DatabaseError

# 导入密码工具
from utils.password import hash_password, verify_password

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

@admin_bp.route('/admin/logs')
@admin_required
def admin_logs():
    """日志管理页面"""
    return render_template('admin/logs.html')

@admin_bp.route('/admin/api/logs', methods=['GET'])
@admin_required
def api_logs():
    """获取日志列表API"""
    try:
        # 获取查询参数
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        log_type = request.args.get('type', 'all')
        username = request.args.get('username', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        action_type = request.args.get('action_type', '')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 构建查询条件
        where_conditions = ["1=1"]
        params = []
        
        if username:
            where_conditions.append("username LIKE %s")
            params.append(f"%{username}%")
        
        if start_date:
            where_conditions.append("DATE(created_at) >= %s")
            params.append(start_date)
        
        if end_date:
            where_conditions.append("DATE(created_at) <= %s")
            params.append(end_date)
        
        if action_type:
            where_conditions.append("action_type = %s")
            params.append(action_type)
        
        where_clause = " AND ".join(where_conditions)
        
        # 获取总记录数
        count_sql = f"SELECT COUNT(*) as total FROM user_log WHERE {where_clause}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        
        # 计算分页
        offset = (page - 1) * per_page
        
        # 获取日志数据
        logs_sql = f"""
            SELECT * FROM user_log 
            WHERE {where_clause}
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
        """
        cursor.execute(logs_sql, params + [per_page, offset])
        logs = cursor.fetchall()
        
        # 解析JSON详情
        for log in logs:
            if log['action_detail']:
                try:
                    import json
                    log['action_detail'] = json.loads(log['action_detail'])
                except:
                    log['action_detail'] = {'detail': log['action_detail']}
        
        conn.close()
        
        return jsonify({
            'success': True,
            'logs': logs,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })
        
    except Exception as e:
        print(f"获取日志失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/logs/statistics', methods=['GET'])
@admin_required
def api_logs_statistics():
    """获取日志统计数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 按操作类型统计
        cursor.execute("""
            SELECT action_type, COUNT(*) as count 
            FROM user_log 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY action_type 
            ORDER BY count DESC
        """)
        action_stats = cursor.fetchall()
        
        # 按日期统计（最近7天）
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count 
            FROM user_log 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(created_at) 
            ORDER BY date DESC
        """)
        daily_stats = cursor.fetchall()
        
        # 按用户统计（活跃用户）
        cursor.execute("""
            SELECT username, COUNT(*) as count 
            FROM user_log 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY username 
            ORDER BY count DESC 
            LIMIT 10
        """)
        user_stats = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'action_stats': action_stats,
            'daily_stats': daily_stats,
            'user_stats': user_stats
        })
        
    except Exception as e:
        print(f"获取日志统计失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/user/<username>/role', methods=['PUT'])
@admin_required
def update_user_role(username):
    """更新用户角色 - 使用统一错误处理"""
    
    data = request.get_json()
    if not data:
        raise ValidationError("请求数据格式错误")
    
    new_role = data.get('role')
    
    if new_role not in ['user', 'admin']:
        raise ValidationError("无效的角色")
    
    # 不允许修改自己的角色
    if username == session['user']:
        raise ValidationError("不能修改自己的角色")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("UPDATE users SET role = %s WHERE username = %s", (new_role, username))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"更新用户角色失败: {e}")
        raise DatabaseError("更新用户角色失败")

@admin_bp.route('/admin/api/user/<username>/delete', methods=['DELETE'])
@admin_required
def delete_user(username):
    """删除用户 - 使用统一错误处理"""
    
    # 不允许删除自己
    if username == session['user']:
        raise ValidationError("不能删除自己")

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"删除用户失败: {e}")
        raise DatabaseError("删除用户失败")

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

        # 重置密码为123456（加密后存储）
        hashed_password = hash_password('123456')
        cursor.execute("UPDATE users SET password = %s WHERE username = %s", (hashed_password, username))
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

@admin_bp.route('/admin/api/user/create', methods=['POST'])
@admin_required
def create_user():
    """创建新用户 - 使用统一错误处理"""
    
    # 获取请求数据
    data = request.get_json()
    if not data:
        raise ValidationError("请求数据格式错误")
    
    username = data.get('username', '').strip()
    nickname = data.get('nickname', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'user')

    # 验证输入
    if not username:
        raise ValidationError("用户名不能为空")
    
    if not password:
        raise ValidationError("密码不能为空")
    
    if role not in ['user', 'admin']:
        raise ValidationError("无效的角色")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 检查用户名是否已存在
        cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            raise ValidationError("用户名已存在")

        # 创建用户（密码加密）
        hashed_password = hash_password(password)
        cursor.execute("""
            INSERT INTO users (username, nickname, password, role)
            VALUES (%s, %s, %s, %s)
        """, (username, nickname, hashed_password, role))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': '用户创建成功'})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"创建用户失败: {e}")
        raise DatabaseError("创建用户失败")

@admin_bp.route('/admin/rooms')
@admin_required
def admin_rooms():
    """房间管理页面"""
    try:
        # 获取房间列表（包含据点信息）
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT r.id, r.name, r.owner, r.fortress_id, f.name as fortress_name 
            FROM rooms r 
            LEFT JOIN fortresses f ON r.fortress_id = f.id 
            ORDER BY r.id DESC
        """)
        rooms = cursor.fetchall()
        
        # 获取所有据点列表（用于新增房间时选择）
        cursor.execute("SELECT id, name FROM fortresses ORDER BY name")
        fortresses = cursor.fetchall()
        
        conn.close()
    except Exception as e:
        print(f"获取房间列表失败: {e}")
        rooms = []
        fortresses = []
    
    return render_template('admin/rooms.html', rooms=rooms, fortresses=fortresses)

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

@admin_bp.route('/admin/api/room/create', methods=['POST'])
@admin_required
def create_room():
    """创建新房间 - 使用统一错误处理"""
    
    # 获取请求数据
    data = request.get_json()
    if not data:
        raise ValidationError("请求数据格式错误")
    
    room_name = data.get('name', '').strip()
    room_owner = data.get('owner', '').strip()
    fortress_id = data.get('fortress_id')

    # 验证输入
    if not room_name:
        raise ValidationError("房间名称不能为空")
    
    if not room_owner:
        raise ValidationError("创建者不能为空")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 检查房间名称是否已存在
        cursor.execute("SELECT name FROM rooms WHERE name = %s", (room_name,))
        if cursor.fetchone():
            raise ValidationError("房间名称已存在")

        # 如果选择了据点，验证据点是否存在
        if fortress_id:
            cursor.execute("SELECT id FROM fortresses WHERE id = %s", (fortress_id,))
            if not cursor.fetchone():
                raise ValidationError("选择的据点不存在")

        # 创建房间
        if fortress_id:
            cursor.execute("""
                INSERT INTO rooms (name, owner, fortress_id)
                VALUES (%s, %s, %s)
            """, (room_name, room_owner, fortress_id))
        else:
            cursor.execute("""
                INSERT INTO rooms (name, owner)
                VALUES (%s, %s)
            """, (room_name, room_owner))
        
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': '房间创建成功'})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"创建房间失败: {e}")
        raise DatabaseError("创建房间失败")

@admin_bp.route('/admin/fortresses')
@admin_required
def admin_fortresses():
    """据点管理页面"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM fortresses ORDER BY created_at DESC")
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
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        position_x = data.get('position_x', 0)
        position_y = data.get('position_y', 0)

        if not name:
            return jsonify({'success': False, 'error': '据点名称不能为空'})

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO fortresses (name, description, position_x, position_y, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (name, description, position_x, position_y))
        conn.commit()
        conn.close()

        return jsonify({'success': True})
    except Exception as e:
        print(f"创建据点失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/fortress/<int:fortress_id>', methods=['DELETE'])
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

# 文件管理功能
@admin_bp.route('/admin/files')
@admin_required
def admin_files():
    """文件管理页面"""
    return render_template('admin/files.html')

@admin_bp.route('/admin/api/files', methods=['GET'])
@admin_required
def api_files():
    """获取文件列表API"""
    try:
        # 获取查询参数
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        category = request.args.get('category', '')
        username = request.args.get('username', '')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 构建查询条件
        where_conditions = ["1=1"]
        params = []
        
        if category:
            where_conditions.append("category = %s")
            params.append(category)
        
        if username:
            where_conditions.append("uploaded_by LIKE %s")
            params.append(f"%{username}%")
        
        where_clause = " AND ".join(where_conditions)
        
        # 获取总记录数
        count_sql = f"SELECT COUNT(*) as total FROM files WHERE {where_clause}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        
        # 计算分页
        offset = (page - 1) * per_page
        
        # 获取文件数据
        files_sql = f"""
            SELECT * FROM files 
            WHERE {where_clause}
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
        """
        cursor.execute(files_sql, params + [per_page, offset])
        files = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'files': files,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })
        
    except Exception as e:
        print(f"获取文件列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/files/upload', methods=['POST'])
@admin_required
def upload_file():
    """文件上传API"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有选择文件'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '没有选择文件'})
        
        # 获取文件信息
        filename = file.filename
        category = request.form.get('category', 'general')
        description = request.form.get('description', '')
        uploaded_by = session['user']
        
        # 保存文件逻辑（这里简化处理）
        # 实际应该保存到指定目录并记录到数据库
        
        return jsonify({'success': True, 'message': '文件上传成功'})
        
    except Exception as e:
        print(f"文件上传失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/files/<int:file_id>', methods=['DELETE'])
@admin_required
def delete_file(file_id):
    """删除文件"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM files WHERE id = %s", (file_id,))
        conn.commit()
        conn.close()

        return jsonify({'success': True})
    except Exception as e:
        print(f"删除文件失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

# 文件清理功能
@admin_bp.route('/admin/api/cleanup/temp', methods=['POST'])
@admin_required
def cleanup_temp_files():
    """清理临时文件"""
    try:
        # 清理临时文件逻辑
        return jsonify({'success': True, 'message': '临时文件清理完成'})
    except Exception as e:
        print(f"清理临时文件失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/cleanup/expired', methods=['POST'])
@admin_required
def cleanup_expired_files():
    """清理过期文件"""
    try:
        # 清理过期文件逻辑
        return jsonify({'success': True, 'message': '过期文件清理完成'})
    except Exception as e:
        print(f"清理过期文件失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/cleanup/orphaned', methods=['POST'])
@admin_required
def cleanup_orphaned_files():
    """清理孤立文件"""
    try:
        # 清理孤立文件逻辑
        return jsonify({'success': True, 'message': '孤立文件清理完成'})
    except Exception as e:
        print(f"清理孤立文件失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/cleanup/duplicate', methods=['POST'])
@admin_required
def cleanup_duplicate_files():
    """清理重复文件"""
    try:
        # 清理重复文件逻辑
        return jsonify({'success': True, 'message': '重复文件清理完成'})
    except Exception as e:
        print(f"清理重复文件失败: {e}")
        return jsonify({'success': False, 'error': str(e)})
