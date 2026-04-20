# TRTC 配置
TRTC_SDKAPPID = 1600138234
TRTC_SECRET_KEY = "db11b7d48e1afd90b0b10bfd9cada42cbf851f43f178ea3204d63deea6044d32"

def gen_user_sig(user_id, expire=86400):
    # 清理用户名
    user_id = ''.join(c for c in user_id if c.isalnum() or c == '_')
    if not user_id:
        user_id = "guest"

    # TODO: 需要下载TLSSigAPIv2.py源码到本地或使用其他方案
    # 目前前端使用手动生成的UserSig进行测试
    raise NotImplementedError("请使用手动生成的UserSig或下载TLSSigAPIv2.py源码")
