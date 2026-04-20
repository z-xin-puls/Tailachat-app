from .TLSSigAPIv2 import TLSSigAPIv2

TRTC_SDKAPPID = 1600138234
TRTC_SECRET_KEY = "db11b7d48e1afd90b0b10bfd9cada42cbf851f43f178ea3204d63deea6044d32"

def gen_user_sig(user_id, expire=604800):
    user_id = ''.join(c for c in user_id if c.isalnum() or c == '_')
    if not user_id:
        user_id = "guest"

    # 使用腾讯云官方库生成UserSig
    api = TLSSigAPIv2(TRTC_SDKAPPID, TRTC_SECRET_KEY)
    user_sig = api.genUserSig(user_id, expire)
    return user_sig
