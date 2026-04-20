import TLSSigAPIv2

# TRTC配置
TRTC_SDKAPPID = 1600138234
TRTC_SECRET_KEY = "db11b7d48e1afd90b0b10bfd9cada42cbf851f43f178ea3204d63deea6044d32"

def gen_user_sig(user_id, expire=86400):
    """
    生成TRTC UserSig（使用官方tls-sig-api-v2-python库）
    
    Args:
        user_id: 用户ID
        expire: 过期时间（秒），默认24小时
    
    Returns:
        UserSig字符串
    """
    api = TLSSigAPIv2.TLSSigAPIv2(TRTC_SDKAPPID, TRTC_SECRET_KEY)
    sig = api.gen_sig(user_id, expire)
    return sig
