import hmac
import hashlib
import base64
import time
import json

# TRTC配置
TRTC_SDKAPPID = 1600138234
TRTC_SECRET_KEY = "db11b7d48e1afd90b0b10bfd9cada42cbf851f43f178ea3204d63deea6044d32"

def gen_user_sig(user_id, expire=86400):
    user_id = ''.join(c for c in user_id if c.isalnum() or c == '_')
    if not user_id:
        user_id = 'guest'
    
    # 原生算法生成 UserSig（不依赖任何库）
    curr_time = int(time.time())
    params = {
        "TLS.ver": "2.0",
        "TLS.identifier": user_id,
        "TLS.sdkappid": TRTC_SDKAPPID,
        "TLS.expire": expire,
        "TLS.time": curr_time
    }

    sign_str = f"TLS.identifier={user_id}&TLS.sdkappid={TRTC_SDKAPPID}&TLS.time={curr_time}&TLS.expire={expire}"
    signature = hmac.new(TRTC_SECRET_KEY.encode(), sign_str.encode(), hashlib.sha256).hexdigest()
    params["TLS.sig"] = signature

    user_sig = base64.b64encode(json.dumps(params).encode()).decode()
    return user_sig
