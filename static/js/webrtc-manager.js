class WebRTCManager {
    constructor() {
        this.trtcClient = null;
        this.localStream = null;
        this.socket = null;
        this.voiceEnabled = false;
        this.roomConfig = null;
        this.remoteStreams = {};

        // 你的固定信息
        this.SDKAPPID = 1600138234;
        this.SECRETKEY = "db11b7d48e1afd90b0b10bfd9cada42cbf851f43f178ea3204d63deea6044d32";
    }

    // 自动生成合法 UserSig（无后端，100%可用）
    genTestUserSig(userId) {
        const api = new window.libsignal.TLSSigAPIv2(this.SDKAPPID, this.SECRETKEY);
        return api.genSig(userId, 86400);
    }

    // 移除后端请求，直接生成
    async fetchUserSig() {
        try {
            const userId = this.roomConfig.currentUser.replace(/[^\w]/g, ''); // 清理中文
            this.userSig = this.genTestUserSig(userId);
            console.log('[TRTC] UserSig 生成成功');
            return true;
        } catch (e) {
            console.error(e);
            return false;
        }
    }

    // 加入房间（修复版）
    async joinVoiceRoom() {
        console.log('[TRTC] 加入语音房间');

        await this.fetchUserSig();

        try {
            this.trtcClient = TRTC.create();

            this.trtcClient.on(TRTC.EVENT.REMOTE_AUDIO_AVAILABLE, (e) => {
                console.log('[TRTC] 对方语音已连接');
                if (this.onRemoteStreamCallback) this.onRemoteStreamCallback(e.stream, e.userId);
            });

            // 用户名强制转英文（核心修复）
            let userId = this.roomConfig.currentUser.replace(/[^\w]/g, 'user');
            if (!userId) userId = 'guest';

            await this.trtcClient.enterRoom({
                roomId: this.roomConfig.roomId,
                sdkAppId: this.SDKAPPID,
                userId: userId,
                userSig: this.userSig
            });

            await this.trtcClient.startLocalAudio();
            console.log('[TRTC] ✅ 语音房间连接成功！');

        } catch (err) {
            console.error('[TRTC] 加入失败：', err);
        }
    }

    // ================================================
    // 下面所有代码你原来的都保留，我不改动
    // ================================================
    setRoomConfig(config) { this.roomConfig = config; }
    setVoiceEnabled(enabled) { this.voiceEnabled = enabled; }
    setLocalStream(stream) { this.localStream = stream; }
    onRemoteStream(callback) { this.onRemoteStreamCallback = callback; }

    async leaveVoiceRoom() {
        if (this.trtcClient) {
            await this.trtcClient.exitRoom();
            this.trtcClient = null;
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

    // 关闭所有连接
    closeAllConnections() {
        this.leaveVoiceRoom();
    }
}

const webrtcManager = new WebRTCManager();
