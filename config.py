# 配置文件
import os

# 数据库配置 - 支持环境变量（Railway + Aiven）
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "root"),
    "database": os.getenv("DB_NAME", "voice_chat"),
    "port": int(os.getenv("DB_PORT", "3306"))
}

# PostgreSQL 连接字符串（用于 psycopg2）
DATABASE_URL = os.getenv("DATABASE_URL")

# Flask配置
SECRET_KEY = "xiao_tt_voice_123"

# 用户验证配置
MAX_USERNAME_LENGTH = 20
MIN_USERNAME_LENGTH = 3
MAX_PASSWORD_LENGTH = 32
MIN_PASSWORD_LENGTH = 6
MAX_ROOM_NAME_LENGTH = 30
MIN_ROOM_NAME_LENGTH = 2

# 头像配置
AVATAR_DIR = os.path.join(os.path.dirname(__file__), "uploads", "avatars")
ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
DEFAULT_AVATAR_URL = "/static/images/avatars/avatar_1.png"
DEFAULT_AVATARS = [
    "/static/images/avatars/avatar_1.png",
    "/static/images/avatars/avatar_2.png", 
    "/static/images/avatars/avatar_3.png",
    "/static/images/avatars/avatar_4.png",
    "/static/images/avatars/avatar_5.png",
    "/static/images/avatars/avatar_6.png",
    "/static/images/avatars/avatar_7.png",
    "/static/images/avatars/avatar_8.png"
]

# 缓存配置
PROFILE_CACHE_TTL_SECONDS = 30

# 创建头像目录
os.makedirs(AVATAR_DIR, exist_ok=True)
