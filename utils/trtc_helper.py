import base64
import hmac
import hashlib
import time
import json

# 你的腾讯云 TRTC 配置
TRTC_SDKAPPID = 1600138234
TRTC_SECRET_KEY = "db11b7d48e1afd90b0b10bfd9cada42cbf851f43f178ea3204d63deea6044d32"

def gen_user_sig(user_id, expire=86400):
    user_id = ''.join(c for c in user_id if c.isalnum() or c == '_')
    if not user_id:
        user_id = "guest"

    # 腾讯云官方 V2 正确签名算法
    curr_time = int(time.time())
    sig_dict = {
        "TLS.ver": "2.0",
        "TLS.identifier": user_id,
        "TLS.sdkappid": TRTC_SDKAPPID,
        "TLS.expire": expire,
        "TLS.time": curr_time,
        "TLS.nonce": curr_time
    }

    plain = "".join([
        f"TLS.identifier={user_id}&",
        f"TLS.sdkappid={TRTC_SDKAPPID}&",
        f"TLS.time={curr_time}&",
        f"TLS.nonce={curr_time}&",
        f"TLS.expire={expire}"
    ])

    # HMAC-SHA256
    sig = hmac.new(
        TRTC_SECRET_KEY.encode("utf-8"),
        plain.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    sig_dict["TLS.sig"] = sig

    # base64
    user_sig = base64.b64encode(json.dumps(sig_dict).encode("utf-8")).decode("utf-8")
    return user_sig
