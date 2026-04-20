// TRTC语音通话管理器
// 使用腾讯云TRTC实现语音通话

// TRTC连接管理器类
class WebRTCManager {
    constructor() {
        this.trtcClient = null;
        this.localStream = null;
        this.socket = null;
        this.voiceEnabled = false;
        this.roomConfig = null;
        this.sdkAppId = 1600138234;
        this.userSig = null;
        this.remoteStreams = {};  // {userId: MediaStream}
    }

    // 设置房间配置
    setRoomConfig(config) {
        this.roomConfig = config;
    }

    // 设置语音启用状态
    setVoiceEnabled(enabled) {
        this.voiceEnabled = enabled;
    }

    // 获取TRTC UserSig
    async fetchUserSig() {
        try {
            const response = await fetch('/api/trtc/usersig');
            if (!response.ok) {
                throw new Error('获取UserSig失败');
            }
            const data = await response.json();
            this.userSig = data.userSig;
            this.sdkAppId = data.sdkAppId;
            console.log('[TRTC] UserSig获取成功');
            return true;
        } catch (error) {
            console.error('[TRTC] 获取UserSig失败:', error);
            return false;
        }
    }

    // 连接Socket.IO服务器
    async connectToSignalingServer() {
        if (!this.roomConfig) {
            console.error('[ERROR] 房间配置未设置');
            return;
        }

        try {
            this.socket = io();

            // 应用存储的聊天回调
            if (this.onChatHistoryCallback) {
                this.socket.on('chat_history', this.onChatHistoryCallback);
            }
            if (this.onChatMessageCallback) {
                this.socket.on('chat_message', this.onChatMessageCallback);
            }
            if (this.onChatErrorCallback) {
                this.socket.on('chat_error', this.onChatErrorCallback);
            }

            this.socket.on('connect', () => {
                console.log('Socket.IO连接成功');
                this.socket.emit('join_chat_room', {
                    room_id: this.roomConfig.roomId,
                    username: this.roomConfig.currentUser
                });
            });

            this.socket.on('disconnect', () => {
                console.log('Socket.IO连接关闭');
                if (this.voiceEnabled) {
                    setTimeout(() => this.connectToSignalingServer(), 3000);
                }
            });

            this.socket.on('user_joined', (data) => {
                console.log('用户加入:', data.username);
                if (this.onUserJoinedCallback) {
                    this.onUserJoinedCallback(data);
                }
            });

            this.socket.on('user_left', (data) => {
                console.log('用户离开:', data.username);
                if (this.onUserLeftCallback) {
                    this.onUserLeftCallback(data);
                }
            });

            this.socket.on('room_users', (data) => {
                console.log('房间用户列表:', data.users);
                if (this.onRoomUsersCallback) {
                    this.onRoomUsersCallback(data);
                }
            });

        } catch (error) {
            console.error('连接Socket.IO失败:', error);
            alert('连接语音服务器失败，请检查网络');
        }
    }

    // 获取socket实例
    getSocket() {
        return this.socket;
    }

    // 设置用户加入回调
    onUserJoined(callback) {
        this.onUserJoinedCallback = callback;
    }

    // 设置用户离开回调
    onUserLeft(callback) {
        this.onUserLeftCallback = callback;
    }

    // 设置房间用户列表回调
    onRoomUsers(callback) {
        this.onRoomUsersCallback = callback;
    }

    // 设置聊天历史回调
    onChatHistory(callback) {
        if (this.socket) {
            this.socket.on('chat_history', callback);
        } else {
            this.onChatHistoryCallback = callback;
        }
    }

    // 设置聊天消息回调
    onChatMessage(callback) {
        if (this.socket) {
            this.socket.on('chat_message', callback);
        } else {
            this.onChatMessageCallback = callback;
        }
    }

    // 设置聊天错误回调
    onChatError(callback) {
        if (this.socket) {
            this.socket.on('chat_error', callback);
        } else {
            this.onChatErrorCallback = callback;
        }
    }

    // 发送聊天消息
    sendChat(message) {
        if (this.socket) {
            this.socket.emit('chat_message', message);
        }
    }

    // 加入语音房间
    async joinVoiceRoom() {
        console.log('[TRTC] 加入语音房间');

        // 获取UserSig
        const success = await this.fetchUserSig();
        if (!success) {
            alert('获取语音凭证失败');
            return;
        }

        try {
            // 创建TRTC对象（v5 API）
            this.trtcClient = TRTC.create();

            // 监听事件
            this.trtcClient.on(TRTC.EVENT.REMOTE_AUDIO_AVAILABLE, (event) => {
                const { userId, stream } = event;
                console.log('[TRTC] 收到远程音频流:', userId);
                if (this.onRemoteStreamCallback) {
                    this.onRemoteStreamCallback(stream, userId);
                }
                this.remoteStreams[userId] = stream;
            });

            this.trtcClient.on(TRTC.EVENT.REMOTE_AUDIO_UNAVAILABLE, (event) => {
                const { userId } = event;
                console.log('[TRTC] 远程音频流移除:', userId);
                delete this.remoteStreams[userId];
            });

            this.trtcClient.on(TRTC.EVENT.USER_LEAVE, (event) => {
                const { userId } = event;
                console.log('[TRTC] 用户离开:', userId);
                delete this.remoteStreams[userId];
            });

            this.trtcClient.on(TRTC.EVENT.ERROR, (error) => {
                console.error('[TRTC] 错误:', error);
            });

            // 加入房间
            await this.trtcClient.enterRoom({
                roomId: this.roomConfig.roomId,
                sdkAppId: this.sdkAppId,
                userId: this.roomConfig.currentUser,
                userSig: this.userSig
            });

            console.log('[TRTC] 成功加入房间');

            // 推流（音频）
            if (this.localStream) {
                await this.trtcClient.startLocalAudio();
                console.log('[TRTC] 成功推流');
            }

        } catch (error) {
            console.error('[TRTC] 加入房间失败:', error);
            alert('加入语音房间失败');
        }
    }

    // 离开语音房间
    async leaveVoiceRoom() {
        console.log('[TRTC] 离开语音房间');

        if (this.trtcClient) {
            try {
                await this.trtcClient.exitRoom();
                this.trtcClient = null;
                this.remoteStreams = {};
                console.log('[TRTC] 成功离开房间');
            } catch (error) {
                console.error('[TRTC] 离开房间失败:', error);
            }
        }
    }

    // 设置本地流
    setLocalStream(stream) {
        this.localStream = stream;
    }

    // 关闭所有连接
    closeAllConnections() {
        this.leaveVoiceRoom();
    }

    // 设置远程流回调
    onRemoteStream(callback) {
        this.onRemoteStreamCallback = callback;
    }
}

// 导出单例实例
const webrtcManager = new WebRTCManager();
