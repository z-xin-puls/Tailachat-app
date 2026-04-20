import hmac
import hashlib
import time
import base64
import json

# TRTC配置
TRTC_SDKAPPID = 1600138234
TRTC_SECRET_KEY = "db11b7d48e1afd90b0b10bfd9cada42cbf851f43f178ea3204d63deea6044d32"

def gen_user_sig(user_id, expire=86400):
    """
    生成TRTC UserSig
    
    Args:
        user_id: 用户ID
        expire: 过期时间（秒），默认24小时
    
    Returns:
        UserSig字符串
    """
    curr_time = int(time.time())
    expire_time = curr_time + expire
    
    # 构造签名数据
    data = {
        "TLS.ver": "2.0",
        "TLS.identifier": user_id,
        "TLS.sdkappid": TRTC_SDKAPPID,
        "TLS.expire": expire_time,
        "TLS.time": curr_time
    }
    
    # 生成签名
    sig_str = json.dumps(data, separators=(',', ':'), sort_keys=True)
    sig = hmac.new(
        TRTC_SECRET_KEY.encode('utf-8'),
        sig_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # 添加签名到数据
    data["TLS.sig"] = sig
    
    # Base64编码
    user_sig = base64.b64encode(json.dumps(data, separators=(',', ':'), sort_keys=True).encode('utf-8')).decode('utf-8')
    
    return user_sig
