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

    # TRTC 官方UserSig公式
    # usersig = hmacsha256(secretkey, (userid + sdkappid + currtime + expire + base64(userid + sdkappid + currtime + expire)))
    curr_time = int(time.time())
    
    # 第一步：拼接字符串
    string_to_hash = f"{user_id}{TRTC_SDKAPPID}{curr_time}{expire}"
    
    # 第二步：base64编码
    base64_string = base64.b64encode(string_to_hash.encode()).decode()
    
    # 第三步：再次拼接
    string_to_sign = f"{user_id}{TRTC_SDKAPPID}{curr_time}{expire}{base64_string}"
    
    # 第四步：HMAC-SHA256
    sig = hmac.new(
        TRTC_SECRET_KEY.encode(),
        string_to_sign.encode(),
        hashlib.sha256
    ).digest()
    
    user_sig = base64.b64encode(sig).decode()
    return user_sig
