import base64
import hmac
import hashlib
import time

# TRTC 配置
TRTC_SDKAPPID = 1600138234
TRTC_SECRET_KEY = "db11b7d48e1afd90b0b10bfd9cada42cbf851f43f178ea3204d63deea6044d32"

def gen_user_sig(user_id, expire=86400):
    # 清理用户名
    user_id = ''.join(c for c in user_id if c.isalnum() or c == '_')
    if not user_id:
        user_id = "guest"

    # TRTC 官方专用算法
    curr_time = int(time.time())
    msg = f"{TRTC_SDKAPPID}\n{user_id}\n{curr_time}\n{expire}\n"
    
    sign = hmac.new(
        TRTC_SECRET_KEY.encode(),
        msg.encode(),
        hashlib.sha1
    ).digest()
    
    user_sig = base64.b64encode(sign).decode()
    return user_sig
