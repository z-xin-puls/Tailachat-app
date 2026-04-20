# coding:utf-8
import hmac
import hashlib
import base64
import zlib
import json
import time


def base64_encode_url(data):
    """ base url encode implementation"""
    base64_data = base64.b64encode(data)
    base64_data_str = bytes.decode(base64_data)
    base64_data_str = base64_data_str.replace('+', '*')
    base64_data_str = base64_data_str.replace('/', '-')
    base64_data_str = base64_data_str.replace('=', '_')
    return base64_data_str


def base64_decode_url(base64_data):
    """ base url decode implementation"""
    base64_data_str = bytes.decode(base64_data)
    base64_data_str = base64_data_str.replace('*', '+')
    base64_data_str = base64_data_str.replace('-', '/')
    base64_data_str = base64_data_str.replace('_', '=')
    raw_data = base64.b64decode(base64_data_str)
    return raw_data


class TLSSigAPIv2:
    __sdkappid = 0
    __version = '2.0'
    __key = ""

    def __init__(self, sdkappid, key):
        self.__sdkappid = sdkappid
        self.__key = key

    ##It is used to generate real-time audio and video (TRTC) business access rights encryption string. For specific usage, please refer to the TRTC document：https://cloud.tencent.com/document/product/647/32240 
    # User-defined userbuf is used for the encrypted string of TRTC service entry permission
    # @brief generate userbuf
    # @param account username
    # @param dwSdkappid sdkappid
    # @param dwAuthID  digital room number
    # @param dwExpTime Expiration time: The expiration time of the encrypted string of this permission. Expiration time = now+dwExpTime
    # @param dwPrivilegeMap User permissions, 255 means all permissions
    # @param dwAccountType User type, default is 0
    # @param roomStr String room number
    # @return userbuf string  returned userbuf
    #/

    def _gen_userbuf(self, account, dwAuthID, dwExpTime,
               dwPrivilegeMap, dwAccountType, roomStr):
        userBuf = b''

        if len(roomStr) > 0 :
            userBuf += bytearray([1])
        else :
            userBuf += bytearray([0])

        userBuf += bytearray([
            ((len(account) & 0xFF00) >> 8),
            (len(account) & 0x00FF),
        ])
        userBuf += bytearray(map(ord, account))

        # dwSdkAppid
        userBuf += bytearray([
            ((self.__sdkappid & 0xFF000000) >> 24),
            ((self.__sdkappid & 0x00FF0000) >> 16),
            ((self.__sdkappid & 0x0000FF00) >> 8),
            (self.__sdkappid & 0x000000FF),
        ])

        # dwAuthId
        userBuf += bytearray([
            ((dwAuthID & 0xFF000000) >> 24),
            ((dwAuthID & 0x00FF0000) >> 16),
            ((dwAuthID & 0x0000FF00) >> 8),
            (dwAuthID & 0x000000FF),
        ])

        #  dwExpTime = now + 300;
        expire = dwExpTime +int(time.time())
        userBuf += bytearray([
            ((expire & 0xFF000000) >> 24),
            ((expire & 0x00FF0000) >> 16),
            ((expire & 0x0000FF00) >> 8),
            (expire & 0x000000FF),
        ])

        # dwPrivilegeMap
        userBuf += bytearray([
            ((dwPrivilegeMap & 0xFF000000) >> 24),
            ((dwPrivilegeMap & 0x00FF0000) >> 16),
            ((dwPrivilegeMap & 0x0000FF00) >> 8),
            (dwPrivilegeMap & 0x000000FF),
        ])

        # dwAccountType
        userBuf += bytearray([
            ((dwAccountType & 0xFF000000) >> 24),
            ((dwAccountType & 0x00FF0000) >> 16),
            ((dwAccountType & 0x0000FF00) >> 8),
            (dwAccountType & 0x000000FF),
        ])
        if len(roomStr) > 0 :
            userBuf += bytearray([
                ((len(roomStr) & 0xFF00) >> 8),
                (len(roomStr) & 0x00FF),
            ])
            userBuf += bytearray(map(ord, roomStr))
        return userBuf
    def __hmacsha256(self, identifier, curr_time, expire, base64_userbuf=None):
        """ Perform hmac through a fixed string, and then base64 it into the value of the sig field """
        raw_content_to_be_signed = "TLS.identifier:" + str(identifier) + "\n"\
                                   + "TLS.sdkappid:" + str(self.__sdkappid) + "\n"\
                                   + "TLS.time:" + str(curr_time) + "\n"\
                                   + "TLS.expire:" + str(expire) + "\n"
        if None != base64_userbuf:
            raw_content_to_be_signed += "TLS.userbuf:" + base64_userbuf + "\n"
        return base64.b64encode(hmac.new(self.__key.encode('utf-8'),
                                         raw_content_to_be_signed.encode('utf-8'),
                                         hashlib.sha256).digest())

    def __gen_sig(self, identifier, expire=180*86400, userbuf=None):
        """ Users can use the default validity period to generate sig """
        curr_time = int(time.time())
        m = dict()
        m["TLS.ver"] = self.__version
        m["TLS.identifier"] = str(identifier)
        m["TLS.sdkappid"] = int(self.__sdkappid)
        m["TLS.expire"] = int(expire)
        m["TLS.time"] = int(curr_time)
        base64_userbuf = None
        if None != userbuf:
            base64_userbuf = bytes.decode(base64.b64encode(userbuf))
            m["TLS.userbuf"] = base64_userbuf

        m["TLS.sig"] = bytes.decode(self.__hmacsha256(
            identifier, curr_time, expire, base64_userbuf))

        raw_sig = json.dumps(m)
        sig_cmpressed = zlib.compress(raw_sig.encode('utf-8'))
        base64_sig = base64_encode_url(sig_cmpressed)
        return base64_sig

    ##
    # Function: Used to issue UserSig that is required by the TRTC and CHAT services.

    #  Parameter description:
    #  userid - User ID. The value can be up to 32 bytes in length and contain letters (a-z and A-Z), digits (0-9), underscores (_), and hyphens (-).
    #  expire - UserSig expiration time, in seconds. For example, 86400 indicates that the generated UserSig will expire one day after being generated.

    def genUserSig(self, userid, expire=180*86400):
        """ Users can use the default validity period to generate sig """
        return self.__gen_sig(userid, expire, None)
    ##
    # Function:
    # Used to issue PrivateMapKey that is optional for room entry.
    # PrivateMapKey must be used together with UserSig but with more powerful permission control capabilities.
    #  - UserSig can only control whether a UserID has permission to use the TRTC service. As long as the UserSig is correct, the user with the corresponding UserID can enter or leave any room.
    #  - PrivateMapKey specifies more stringent permissions for a UserID, including whether the UserID can be used to enter a specific room and perform audio/video upstreaming in the room.
    # To enable stringent PrivateMapKey permission bit verification, you need to enable permission key in TRTC console > Application Management > Application Info.
    #      *
    # Parameter description:
    # userid - User ID. The value can be up to 32 bytes in length and contain letters (a-z and A-Z), digits (0-9), underscores (_), and hyphens (-).
    # roomid - ID of the room to which the specified UserID can enter.
    # expire - PrivateMapKey expiration time, in seconds. For example, 86400 indicates that the generated PrivateMapKey will expire one day after being generated.
    # privilegeMap - Permission bits. Eight bits in the same byte are used as the permission switches of eight specific features:
    #  - Bit 1: 0000 0001 = 1, permission for room creation
    #  - Bit 2: 0000 0010 = 2, permission for room entry
    #  - Bit 3: 0000 0100 = 4, permission for audio sending
    #  - Bit 4: 0000 1000 = 8, permission for audio receiving
    #  - Bit 5: 0001 0000 = 16, permission for video sending
    #  - Bit 6: 0010 0000 = 32, permission for video receiving
    #  - Bit 7: 0100 0000 = 64, permission for substream video sending (screen sharing)
    #  - Bit 8: 1000 0000 = 200, permission for substream video receiving (screen sharing)
    #  - privilegeMap == 1111 1111 == 255: Indicates that the UserID has all feature permissions of the room specified by roomid.
    #  - privilegeMap == 0010 1010 == 42: Indicates that the UserID has only the permissions to enter the room and receive audio/video data.

    def genPrivateMapKey(self, userid, expire, roomid, privilegeMap):
        """ Contains userbuf to generate signature """
        userbuf = self._gen_userbuf(userid,roomid,expire,privilegeMap,0,"")
        print(userbuf)
        return self.__gen_sig(userid, expire, userbuf)

    ##
    # Function:
    #  Used to issue PrivateMapKey that is optional for room entry.
    #  PrivateMapKey must be used together with UserSig but with more powerful permission control capabilities.
