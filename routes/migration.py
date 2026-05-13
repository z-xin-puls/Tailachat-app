# 数据库迁移路由
"""
用于在Railway等云平台上执行数据库迁移
通过HTTP接口触发密码迁移操作
"""

from flask import Blueprint, request, jsonify, session
from models.database import get_db_connection
from utils.password import hash_password, verify_password, is_hashed_password
from utils.exceptions import AppError, AuthenticationError, DatabaseError
from utils.decorators import admin_required

# 创建蓝图
migration_bp = Blueprint('migration', __name__)

@migration_bp.route('/admin/migration/status', methods=['GET'])
@admin_required
def check_migration_status():
    """检查密码迁移状态"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 统计密码状态
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as encrypted FROM users WHERE password LIKE '$2b$%'")
        encrypted_users = cursor.fetchone()[0]
        
        plain_users = total_users - encrypted_users
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total_users': total_users,
                'encrypted_users': encrypted_users,
                'plain_users': plain_users,
                'migration_needed': plain_users > 0,
                'migration_percentage': round((encrypted_users / total_users) * 100, 2) if total_users > 0 else 100
            }
        })
        
    except Exception as e:
        print(f"检查迁移状态失败: {e}")
        raise DatabaseError("检查迁移状态失败")

@migration_bp.route('/admin/migration/prepare', methods=['POST'])
@admin_required
def prepare_migration():
    """准备迁移 - 修改密码字段长度"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查当前密码字段长度
        cursor.execute("""
            SELECT CHARACTER_MAXIMUM_LENGTH 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'password'
        """)
        result = cursor.fetchone()
        
        if result:
            current_length = result[0]
            
            if current_length < 60:
                # 修改密码字段长度
                cursor.execute("ALTER TABLE users MODIFY COLUMN password VARCHAR(100)")
                conn.commit()
                message = f"密码字段长度已从 {current_length} 修改为 100"
            else:
                message = f"密码字段长度已足够: {current_length}"
        else:
            raise DatabaseError("无法找到密码字段信息")
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        print(f"准备迁移失败: {e}")
        raise DatabaseError("准备迁移失败")

@migration_bp.route('/admin/migration/execute', methods=['POST'])
@admin_required
def execute_migration():
    """执行密码迁移"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 获取所有明文密码用户
        cursor.execute("""
            SELECT id, username, password 
            FROM users 
            WHERE password NOT LIKE '$2b$%'
            ORDER BY id
        """)
        users = cursor.fetchall()
        
        migrated_count = 0
        failed_count = 0
        failed_users = []
        
        for user in users:
            user_id = user['id']
            username = user['username']
            password = user['password']
            
            try:
                # 加密密码
                hashed_password = hash_password(password)
                cursor.execute("UPDATE users SET password = %s WHERE id = %s", 
                             (hashed_password, user_id))
                migrated_count += 1
                print(f"✅ 已迁移用户 {username} (ID: {user_id})")
                
            except Exception as e:
                failed_count += 1
                failed_users.append({
                    'username': username,
                    'id': user_id,
                    'error': str(e)
                })
                print(f"❌ 迁移用户 {username} (ID: {user_id}) 失败: {e}")
        
        # 提交更改
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'migrated_count': migrated_count,
                'failed_count': failed_count,
                'failed_users': failed_users
            },
            'message': f"迁移完成: 成功 {migrated_count} 个，失败 {failed_count} 个"
        })
        
    except Exception as e:
        print(f"执行迁移失败: {e}")
        raise DatabaseError("执行迁移失败")

@migration_bp.route('/admin/migration/verify', methods=['POST'])
@admin_required
def verify_migration():
    """验证迁移结果"""
    try:
        # 测试几个用户的密码验证
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT username, password FROM users LIMIT 5")
        users = cursor.fetchall()
        
        verification_results = []
        
        for user in users:
            username = user['username']
            stored_password = user['password']
            
            # 检查是否为bcrypt格式
            is_hashed = is_hashed_password(stored_password)
            
            verification_results.append({
                'username': username,
                'is_hashed': is_hashed,
                'password_length': len(stored_password),
                'password_preview': stored_password[:20] + "..." if len(stored_password) > 20 else stored_password
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': verification_results
        })
        
    except Exception as e:
        print(f"验证迁移失败: {e}")
        raise DatabaseError("验证迁移失败")

@migration_bp.route('/admin/migration', methods=['GET'])
@admin_required
def migration_dashboard():
    """迁移管理页面"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>密码迁移管理</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f8fafc; 
                padding: 20px;
            }
            .container { 
                max-width: 800px; 
                margin: 0 auto; 
                background: white; 
                border-radius: 12px; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                padding: 30px; 
                text-align: center;
            }
            .content { padding: 30px; }
            .section { 
                margin-bottom: 30px; 
                padding: 20px; 
                border: 1px solid #e5e7eb; 
                border-radius: 8px;
                background: #f9fafb;
            }
            .btn { 
                background: #3b82f6; 
                color: white; 
                border: none; 
                padding: 12px 24px; 
                border-radius: 6px; 
                cursor: pointer; 
                margin: 5px;
                font-size: 14px;
                transition: background 0.2s;
            }
            .btn:hover { background: #2563eb; }
            .btn.danger { background: #ef4444; }
            .btn.danger:hover { background: #dc2626; }
            .btn.success { background: #10b981; }
            .btn.success:hover { background: #059669; }
            .status { 
                padding: 10px; 
                border-radius: 6px; 
                margin: 10px 0; 
            }
            .status.info { background: #dbeafe; color: #1e40af; }
            .status.success { background: #d1fae5; color: #065f46; }
            .status.warning { background: #fef3c7; color: #92400e; }
            .status.error { background: #fee2e2; color: #991b1b; }
            .progress { 
                width: 100%; 
                height: 20px; 
                background: #e5e7eb; 
                border-radius: 10px; 
                overflow: hidden;
                margin: 10px 0;
            }
            .progress-bar { 
                height: 100%; 
                background: linear-gradient(90deg, #3b82f6, #8b5cf6); 
                transition: width 0.3s;
            }
            .log { 
                background: #1f2937; 
                color: #f3f4f6; 
                padding: 15px; 
                border-radius: 6px; 
                font-family: monospace; 
                font-size: 12px;
                max-height: 200px;
                overflow-y: auto;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 密码迁移管理</h1>
                <p>Railway部署环境密码加密迁移工具</p>
            </div>
            <div class="content">
                <div class="section">
                    <h3>📊 迁移状态</h3>
                    <div id="status">检查中...</div>
                    <div class="progress">
                        <div class="progress-bar" id="progress-bar" style="width: 0%"></div>
                    </div>
                </div>
                
                <div class="section">
                    <h3>🔧 迁移操作</h3>
                    <button class="btn" onclick="checkStatus()">📋 检查状态</button>
                    <button class="btn" onclick="prepareMigration()">🛠️ 准备迁移</button>
                    <button class="btn danger" onclick="executeMigration()">🚀 执行迁移</button>
                    <button class="btn success" onclick="verifyMigration()">✅ 验证结果</button>
                </div>
                
                <div class="section">
                    <h3>📝 操作日志</h3>
                    <div class="log" id="log">等待操作...</div>
                </div>
            </div>
        </div>

        <script>
            function log(message) {
                const logEl = document.getElementById('log');
                const timestamp = new Date().toLocaleTimeString();
                logEl.innerHTML += `[${timestamp}] ${message}\\n`;
                logEl.scrollTop = logEl.scrollHeight;
            }

            function updateStatus(data) {
                const statusEl = document.getElementById('status');
                const progressBar = document.getElementById('progress-bar');
                
                const percentage = data.migration_percentage;
                progressBar.style.width = percentage + '%';
                
                let statusClass = 'info';
                let statusText = '';
                
                if (data.migration_needed) {
                    statusClass = 'warning';
                    statusText = `⚠️ 需要迁移: ${data.plain_users}/${data.total_users} 个用户使用明文密码`;
                } else {
                    statusClass = 'success';
                    statusText = `✅ 迁移完成: ${data.encrypted_users}/${data.total_users} 个用户已加密`;
                }
                
                statusEl.className = `status ${statusClass}`;
                statusEl.innerHTML = statusText + `<br><small>完成度: ${percentage}%</small>`;
            }

            async function checkStatus() {
                log('📋 检查迁移状态...');
                try {
                    const response = await fetch('/admin/migration/status');
                    const data = await response.json();
                    if (data.success) {
                        updateStatus(data.data);
                        log('✅ 状态检查完成');
                    } else {
                        log('❌ 状态检查失败: ' + data.error);
                    }
                } catch (error) {
                    log('❌ 网络错误: ' + error.message);
                }
            }

            async function prepareMigration() {
                log('🛠️ 准备迁移...');
                try {
                    const response = await fetch('/admin/migration/prepare', { method: 'POST' });
                    const data = await response.json();
                    if (data.success) {
                        log('✅ ' + data.message);
                    } else {
                        log('❌ 准备失败: ' + data.error);
                    }
                } catch (error) {
                    log('❌ 网络错误: ' + error.message);
                }
            }

            async function executeMigration() {
                if (!confirm('确定要执行密码迁移吗？此操作不可逆！')) {
                    return;
                }
                
                log('🚀 开始执行迁移...');
                try {
                    const response = await fetch('/admin/migration/execute', { method: 'POST' });
                    const data = await response.json();
                    if (data.success) {
                        const result = data.data;
                        log(`✅ 迁移完成: 成功 ${result.migrated_count} 个，失败 ${result.failed_count} 个`);
                        
                        if (result.failed_users.length > 0) {
                            log('❌ 失败的用户:');
                            result.failed_users.forEach(user => {
                                log(`   - ${user.username}: ${user.error}`);
                            });
                        }
                        
                        // 刷新状态
                        setTimeout(checkStatus, 1000);
                    } else {
                        log('❌ 迁移失败: ' + data.error);
                    }
                } catch (error) {
                    log('❌ 网络错误: ' + error.message);
                }
            }

            async function verifyMigration() {
                log('✅ 验证迁移结果...');
                try {
                    const response = await fetch('/admin/migration/verify', { method: 'POST' });
                    const data = await response.json();
                    if (data.success) {
                        log('📋 验证结果:');
                        data.data.forEach(user => {
                            const status = user.is_hashed ? '✅' : '❌';
                            log(`   ${status} ${user.username}: ${user.password_preview} (${user.password_length} 字符)`);
                        });
                    } else {
                        log('❌ 验证失败: ' + data.error);
                    }
                } catch (error) {
                    log('❌ 网络错误: ' + error.message);
                }
            }

            // 页面加载时自动检查状态
            window.onload = function() {
                checkStatus();
            };
        </script>
    </body>
    </html>
    '''