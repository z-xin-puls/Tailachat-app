# 房间相关数据模型
from models.database import get_db_connection
from utils.validators import validate_room_name

def get_all_rooms():
    """获取所有房间"""
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name, owner, fortress_id FROM rooms")
    rooms = cursor.fetchall()
    db.close()
    return rooms

def create_room(name, owner):
    """创建房间"""
    error = validate_room_name(name)
    if error:
        return None, error
    
    db = get_db_connection()
    cursor = db.cursor()
    
    cursor.execute("INSERT INTO rooms (name, owner) VALUES (%s, %s)", (name, owner))
    
    db.commit()
    room_id = cursor.lastrowid
    db.close()
    return room_id, None

def create_room_with_fortress(name, owner, fortress_id):
    """创建房间并关联据点"""
    error = validate_room_name(name)
    if error:
        return None, error
    
    db = get_db_connection()
    cursor = db.cursor()
    
    cursor.execute("INSERT INTO rooms (name, owner, fortress_id) VALUES (%s, %s, %s)", 
                   (name, owner, fortress_id))
    
    db.commit()
    room_id = cursor.lastrowid
    db.close()
    return room_id, None

def get_room_by_id(room_id):
    """根据ID获取房间"""
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM rooms WHERE id = %s", (room_id,))
    room = cursor.fetchone()
    db.close()
    return room
