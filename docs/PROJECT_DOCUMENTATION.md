# 小T语音 - 明日方舟主题语音聊天应用

## 项目概述

小T语音是一个基于 Flask 的语音聊天 Web 应用，采用明日方舟（Arknights）游戏主题风格，提供房间创建、实时聊天、语音通话等功能。

## 技术栈

| 分类 | 技术 | 版本 |
|------|------|------|
| **框架** | Flask | 2.x |
| **实时通信** | Flask-SocketIO | 5.x |
| **数据库** | MySQL | 8.0+ |
| **语音通话** | WebRTC | 原生 API |
| **部署** | Gunicorn + Gevent | 最新 |
| **密码加密** | bcrypt | 4.x |

## 项目结构

```
PythonProject1/
├── app.py                          # Flask主应用入口
├── config.py                       # 应用配置文件
├── init_db.py                      # 数据库初始化
├── start_webrtc.py                 # 启动脚本
├── requirements.txt                # 依赖列表
├── docs/                           # 文档目录
│   └── REFACTORING_DOCUMENTATION.md# 重构文档
├── models/                         # 数据模型层
│   ├── __init__.py
│   ├── database.py                 # 数据库连接和操作
│   ├── user.py                     # 用户数据模型
│   ├── room.py                     # 房间数据模型
│   ├── analytics.py                # 数据分析模块
│   └── charts.py                   # 图表生成模块
├── routes/                         # 路由控制器
│   ├── __init__.py
│   ├── auth.py                     # 认证路由（登录/注册）
│   ├── main.py                     # 主页路由
│   ├── profile.py                  # 个人资料路由
│   └── admin.py                    # 管理员路由
├── utils/                          # 工具函数
│   ├── __init__.py
│   ├── password.py                 # 密码加密工具
│   ├── validators.py               # 数据验证工具
│   ├── decorators.py               # 装饰器
│   ├── exceptions.py               # 自定义异常
│   ├── helpers.py                  # 辅助函数
│   ├── logger.py                   # 日志工具
│   ├── trtc_helper.py              # 腾讯云TRTC集成
│   └── TLSSigAPIv2.py              # TLS签名API
├── static/                         # 静态资源
│   ├── css/                        # 样式文件
│   │   ├── Arknights.css           # 明日方舟主题样式
│   │   ├── main.css                # 主页样式
│   │   └── room.css                # 房间页面样式
│   ├── js/                         # JavaScript文件
│   │   ├── main.js                 # 主页脚本
│   │   ├── room.js                 # 房间页面脚本
│   │   └── webrtc-manager.js       # WebRTC管理器
│   └── images/                     # 图片资源
│       ├── avatars/                # 用户头像（8个默认头像）
│       ├── img/                    # 势力图标
│       ├── namecard/               # 名片背景
│       ├── room/                   # 房间背景
│       └── map/                    # 地图图片
├── templates/                      # HTML模板
│   ├── admin/                      # 管理后台模板
│   ├── main/                       # 主页模板
│   └── rooms/                      # 房间页面模板
└── uploads/                        # 上传文件目录
    └── avatars/                    # 用户上传的头像
```

## 功能特性

### 核心功能

| 功能 | 描述 |
|------|------|
| **用户认证** | 用户名/密码登录注册，密码bcrypt加密 |
| **房间系统** | 创建、加入、退出语音房间 |
| **实时聊天** | WebSocket文字聊天 |
| **语音通话** | WebRTC点对点语音通信 |
| **个人资料** | 头像上传、资料编辑 |
| **管理后台** | 用户管理、房间管理、日志查看 |
| **房主权限** | 踢人、禁言用户 |

### 明日方舟主题特色

- 🎨 **主题配色**: 明日方舟红色主色调 (#ff7878)
- 🖼️ **视觉资源**: 8个明日方舟风格头像、势力图标、名片背景
- ✨ **特效**: 红色光晕效果、毛玻璃卡片

## 快速开始

### 环境要求

- Python 3.10+
- MySQL 8.0+

### 安装依赖

```bash
pip install -r requirements.txt
```

### 数据库配置

在 `config.py` 中配置数据库连接：

```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "your_password",
    "database": "voice_chat",
    "port": 3306
}
```

### 初始化数据库

```bash
python init_db.py
```

### 启动应用

```bash
# 开发模式
python start_webrtc.py

# 或直接运行
python app.py
```

启动后访问: http://127.0.0.1:5000

## API 接口

### 认证接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/login` | POST | 用户登录 |
| `/register` | POST | 用户注册 |
| `/logout` | GET | 用户登出 |

### 房间接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/room/<id>` | GET | 进入房间 |
| `/create` | POST | 创建房间 |

### 个人资料接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/profile` | GET/POST | 个人资料 |
| `/profile/avatar` | POST | 上传头像 |
| `/user/<username>` | GET | 查看用户资料 |

### 管理接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/admin` | GET | 管理后台 |
| `/admin/api/users` | GET | 获取用户列表 |
| `/admin/api/rooms` | GET | 获取房间列表 |
| `/admin/api/logs` | GET | 获取日志 |

## 配置说明

### 主要配置项 (`config.py`)

```python
# Flask配置
SECRET_KEY = "your_secret_key"  # 会话密钥

# 用户验证配置
MAX_USERNAME_LENGTH = 20
MIN_USERNAME_LENGTH = 3
MAX_PASSWORD_LENGTH = 32
MIN_PASSWORD_LENGTH = 6

# 头像配置
DEFAULT_AVATAR_URL = "/static/images/avatars/avatar_1.png"
DEFAULT_AVATARS = [
    "/static/images/avatars/avatar_1.png",
    "/static/images/avatars/avatar_2.png",
    # ... 共8个默认头像
]

# 缓存配置
PROFILE_CACHE_TTL_SECONDS = 30
```

### 环境变量支持

支持通过环境变量覆盖配置：

| 环境变量 | 对应配置 |
|----------|----------|
| `MYSQLHOST` / `DB_HOST` | 数据库主机 |
| `MYSQLUSER` / `DB_USER` | 数据库用户 |
| `MYSQLPASSWORD` / `DB_PASSWORD` | 数据库密码 |
| `MYSQLDATABASE` / `DB_NAME` | 数据库名称 |
| `MYSQLPORT` / `DB_PORT` | 数据库端口 |

## 部署指南

### 生产环境部署

```bash
# 使用Gunicorn启动
gunicorn -w 4 -k gevent app:app

# 或使用SocketIO专用启动方式
gunicorn -w 4 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker app:app
```

### Nginx配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

## 开发规范

### 代码风格

- 使用 PEP 8 规范
- 使用类型提示
- 使用 docstring 注释

### 提交规范

```
feat: 添加新功能
fix: 修复bug
docs: 更新文档
style: 代码格式调整
refactor: 代码重构
test: 添加测试
```

## 许可证

MIT License

## 更新日志

### 2026-05-14 - 功能修复与优化

| 修复内容 | 描述 | 影响文件 |
|---------|------|---------|
| **禁言功能修复** | 添加禁言状态检查，被禁言用户无法发送消息 | `app.py:683-686` |
| **踢人功能优化** | 优化用户查找和数据清理逻辑，确保彻底移除被踢用户 | `app.py:766-787` |
| **缺失导入修复** | 添加 `AuthorizationError` 导入，修复权限错误处理 | `routes/profile.py:5` |
| **数据库游标统一** | 将普通游标统一改为字典游标（`dictionary=True`），修复数据访问错误 | `routes/main.py`, `routes/profile.py` |
| **重复变量移除** | 移除 `app.py` 中重复定义的 `room_users` 变量 | `app.py:57` |
| **前端禁言状态检查** | 房间初始化时主动检查禁言状态 | `static/js/room.js:629-630` |

## 贡献

欢迎提交 Issue 和 Pull Request！