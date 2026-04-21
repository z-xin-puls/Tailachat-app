# 数据分析统计模型
from models.database import get_db_connection
from datetime import datetime, timedelta

def get_dashboard_stats(online_users=0, active_rooms=0):
    """获取仪表盘统计数据"""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # 当前在线用户数（从SocketIO全局变量获取）
        # online_users 参数由调用方传入
        
        # 今日活跃用户数
        today = datetime.now().date()
        cursor.execute("""
            SELECT COUNT(DISTINCT username) 
            FROM user_activity 
            WHERE DATE(timestamp) = %s
        """, (today,))
        today_active_users = cursor.fetchone()[0]
        
        # 活跃房间数（从参数传入）
        # active_rooms 参数由调用方传入
        
        # 今日房间创建数
        cursor.execute("""
            SELECT COUNT(*) 
            FROM room_activity 
            WHERE action = 'create' AND DATE(timestamp) = %s
        """, (today,))
        today_created_rooms = cursor.fetchone()[0]
        
        # 总用户数
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        # 总房间数
        cursor.execute("SELECT COUNT(*) FROM rooms")
        total_rooms = cursor.fetchone()[0]
        
        # 总据点数
        cursor.execute("SELECT COUNT(*) FROM fortresses")
        total_fortresses = cursor.fetchone()[0]
        
        # 管理员数
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        db.close()
        
        return {
            'online_users': online_users,
            'today_active_users': today_active_users,
            'active_rooms': active_rooms,
            'today_created_rooms': today_created_rooms,
            'total_users': total_users,
            'total_rooms': total_rooms,
            'total_fortresses': total_fortresses,
            'admin_count': admin_count
        }
    except Exception as e:
        print(f"获取仪表盘统计数据失败: {e}")
        return {
            'online_users': 0,
            'today_active_users': 0,
            'active_rooms': 0,
            'today_created_rooms': 0,
            'total_users': 0,
            'total_rooms': 0,
            'total_fortresses': 0,
            'admin_count': 0
        }

def get_user_growth_trend(days=7):
    """获取用户增长趋势"""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        trend_data = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).date()
            cursor.execute("""
                SELECT COUNT(DISTINCT username) 
                FROM user_activity 
                WHERE DATE(timestamp) = %s
            """, (date,))
            count = cursor.fetchone()[0]
            trend_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'count': count
            })
        
        trend_data.reverse()
        db.close()
        return trend_data
    except Exception as e:
        print(f"获取用户增长趋势失败: {e}")
        return []

def get_room_creation_trend(days=7):
    """获取房间创建趋势"""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        trend_data = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).date()
            cursor.execute("""
                SELECT COUNT(*) 
                FROM room_activity 
                WHERE action = 'create' AND DATE(timestamp) = %s
            """, (date,))
            count = cursor.fetchone()[0]
            trend_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'count': count
            })
        
        trend_data.reverse()
        db.close()
        return trend_data
    except Exception as e:
        print(f"获取房间创建趋势失败: {e}")
        return []
