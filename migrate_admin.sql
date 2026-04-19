-- 管理员功能数据库迁移脚本
-- 执行前请备份数据库

-- 1. 添加 role 字段到 users 表
ALTER TABLE users ADD COLUMN role ENUM('user', 'admin') DEFAULT 'user';

-- 2. 添加索引提升查询性能
ALTER TABLE users ADD INDEX idx_role (role);

-- 3. 设置初始管理员账号（请修改下面的用户名和密码）
-- 方式1: 将现有用户升级为管理员（同时修改密码）
-- 将 'your_admin_username' 替换为你的管理员用户名
-- 将 'your_admin_password' 替换为你的管理员密码（明文，与注册时相同）
UPDATE users SET role = 'admin', password = 'your_admin_password' WHERE username = 'your_admin_username';

-- 方式2: 如果没有现有用户，插入一个新的管理员账号
-- INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin');

-- 验证修改
SELECT username, role FROM users WHERE role = 'admin';
