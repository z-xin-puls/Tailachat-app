import json
import base64
import hmac
import hashlib
import time

TRTC_SDKAPPID = 1600138234
TRTC_SECRET_KEY = "db11b7d48e1afd90b0b10bfd9cada42cbf851f43f178ea3204d63deea6044d32"

def gen_user_sig(user_id, expire=604800):
    user_id = ''.join(c for c in user_id if c.isalnum() or c == '_')
    if not user_id:
        user_id = "guest"

    now = int(time.time())
    payload = {
        "TLS.ver": "2.0",
        "TLS.sdkappid": TRTC_SDKAPPID,
        "TLS.identifier": user_id,
        "TLS.time": now,
        "TLS.expire": expire
    }

    plain = f"TLS.ver=2.0&TLS.sdkappid={TRTC_SDKAPPID}&TLS.identifier={user_id}&TLS.time={now}&TLS.expire={expire}"
    sig = hmac.new(TRTC_SECRET_KEY.encode('utf-8'), plain.encode('utf-8'), hashlib.sha256).digest()
    payload["TLS.sig"] = base64.b64encode(sig).decode()

    json_str = json.dumps(payload, separators=(',', ':'))
    return base64.b64encode(json_str.encode()).decode()
