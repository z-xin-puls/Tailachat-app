# Railway部署密码迁移指南

## 🚀 部署步骤

### 1. 部署前准备
确保你的代码已经包含：
- ✅ bcrypt在requirements.txt中
- ✅ 密码加密代码已实现
- ✅ 迁移路由已添加

### 2. 部署到Railway
```bash
git add .
git commit -m "添加密码加密和迁移功能"
git push origin main
```

### 3. 在Railway上执行迁移

#### 方法一：通过管理界面（推荐）
1. 访问：`https://your-app.railway.app/admin/migration`
2. 使用管理员账号登录
3. 按照界面提示执行迁移

#### 方法二：通过API调用
```bash
# 1. 检查迁移状态
curl -X GET https://your-app.railway.app/admin/migration/status \
  -H "Cookie: your-session-cookie"

# 2. 准备迁移（修改字段长度）
curl -X POST https://your-app.railway.app/admin/migration/prepare \
  -H "Cookie: your-session-cookie"

# 3. 执行迁移
curl -X POST https://your-app.railway.app/admin/migration/execute \
  -H "Cookie: your-session-cookie"

# 4. 验证结果
curl -X POST https://your-app.railway.app/admin/migration/verify \
  -H "Cookie: your-session-cookie"
```

## 🔧 迁移API说明

### 检查状态
- **URL**: `GET /admin/migration/status`
- **返回**: 用户密码加密状态统计

### 准备迁移
- **URL**: `POST /admin/migration/prepare`
- **功能**: 修改密码字段长度为VARCHAR(100)

### 执行迁移
- **URL**: `POST /admin/migration/execute`
- **功能**: 将所有明文密码转换为bcrypt哈希

### 验证结果
- **URL**: `POST /admin/migration/verify`
- **功能**: 验证迁移结果

## ⚠️ 注意事项

1. **备份数据**: 迁移前建议备份数据库
2. **管理员权限**: 只有管理员可以执行迁移
3. **不可逆操作**: 密码一旦加密无法恢复明文
4. **测试环境**: 建议先在测试环境验证

## 🎯 迁移完成后

- 所有用户密码都是bcrypt加密
- 用户需要使用原密码登录（无需重置）
- 新用户注册自动使用bcrypt加密
- 密码修改功能正常工作

## 📞 故障排除

如果迁移失败：
1. 检查Railway日志
2. 确认数据库连接正常
3. 验证bcrypt库是否正确安装
4. 检查用户权限
