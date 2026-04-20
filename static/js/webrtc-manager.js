// WebRTC和Socket.IO连接管理器
// 专门处理WebRTC连接配置、ICE服务器管理、Socket.IO信令管理

// Xirsys凭据配置
const XIRSYS_CONFIG = {
    apiUrl: "https://global.xirsys.net/_turn/MyFirstApp",
    username: "ZhiX",
    secret: "e2aeaa88-3c93-11f1-9760-0242ac130006"
};

// 默认ICE服务器配置（Xirsys动态获取后更新）
let iceServers = {
    iceServers: [
        // Google STUN作为备用
        { urls: "stun:stun.l.google.com:19302" }
    ],
    iceCandidatePoolSize: 10,
    iceTransportPolicy: "all"
};

// 获取Xirsys TURN凭据
async function fetchXirsysCredentials() {
    try {
        console.log('[Xirsys] 获取TURN凭据...');
        const basicAuth = btoa(`${XIRSYS_CONFIG.username}:${XIRSYS_CONFIG.secret}`);

        const response = await fetch(XIRSYS_CONFIG.apiUrl, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Basic ${basicAuth}`
            },
            body: JSON.stringify({ format: "urls" })
        });

        const data = await response.json();
        console.log('[Xirsys] 完整返回结果:', data);

        if (data.s === 'ok' && data.v) {
            // Xirsys返回的ICE服务器配置
            // data.v.iceServers 可能是单个对象或数组
            if (!Array.isArray(data.v.iceServers)) {
                // 如果是单个对象，转换为数组格式
                data.v.iceServers = [data.v.iceServers];
            }
            iceServers = data.v;
            console.log('[Xirsys] ✅ 凭据获取成功，ICE服务器已更新');
            console.log('[Xirsys] ICE服务器配置:', iceServers);
            console.log('[Xirsys] ICE服务器列表:', iceServers.iceServers);
            console.log('[Xirsys] iceServers是否为数组:', Array.isArray(iceServers.iceServers));
            return true;
        } else {
            console.error('[Xirsys] ❌ 凭据获取失败:', data);
            return false;
        }
    } catch (error) {
        console.error('[Xirsys] 💥 获取凭据出错:', error);
        return false;
    }
}

// WebRTC连接管理器类
class WebRTCManager {
    constructor() {
        this.peerConnections = {};  // {username: RTCPeerConnection}
        this.iceCandidateQueues = {};  // {username: [candidate]} - 缓存ICE候选
        this.localStream = null;
        this.socket = null;
        this.voiceEnabled = false;
        this.roomConfig = null;
    }

    // 设置房间配置
    setRoomConfig(config) {
        this.roomConfig = config;
    }

    // 设置语音启用状态
    setVoiceEnabled(enabled) {
        this.voiceEnabled = enabled;
    }

    // 连接Socket.IO服务器
    async connectToSignalingServer() {
        if (!this.roomConfig) {
            console.error('[ERROR] 房间配置未设置');
            return;
        }

        // 获取Xirsys TURN凭据
        await fetchXirsysCredentials();

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
                // 加入聊天房间（页面加载时就加入）
                this.socket.emit('join_chat_room', {
                    room_id: this.roomConfig.roomId,
                    username: this.roomConfig.currentUser
                });
                // 语音房间在启动语音时才加入
            });

            this.socket.on('disconnect', () => {
                console.log('Socket.IO连接关闭');
                if (this.voiceEnabled) {
                    // 自动重连
                    setTimeout(() => this.connectToSignalingServer(), 3000);
                }
            });

            this.socket.on('user_joined', (data) => {
                console.log('用户加入:', data.username);
                // 只有在自己已加入语音房间时，才向新用户发送offer
                if (this.voiceEnabled) {
                    this.createPeerConnection(data.username, true);
                }
                if (this.onUserJoinedCallback) {
                    this.onUserJoinedCallback(data);
                }
            });

            this.socket.on('user_left', (data) => {
                console.log('用户离开:', data.username);
                // 关闭与该用户的连接
                this.closePeerConnection(data.username);
                if (this.onUserLeftCallback) {
                    this.onUserLeftCallback(data);
                }
            });

            this.socket.on('room_users', (data) => {
                console.log('房间用户列表:', data.users);
                // 只有在自己已加入语音房间时，才与房间内现有用户建立连接
                if (this.voiceEnabled) {
                    for (const username of data.users) {
                        this.createPeerConnection(username, false);
                    }
                }
                if (this.onRoomUsersCallback) {
                    this.onRoomUsersCallback(data);
                }
            });

            this.socket.on('webrtc_offer', async (data) => {
                console.log('收到offer from:', data.sender);
                const answer = await this.handleOffer(data);
                this.socket.emit('webrtc_answer', {
                    sdp: answer,
                    target: data.sender,
                    sender: this.roomConfig.currentUser
                });
            });

            this.socket.on('webrtc_answer', async (data) => {
                console.log('收到answer from:', data.sender);
                await this.handleAnswer(data);
            });

            this.socket.on('ice_candidate', async (data) => {
                console.log('收到ICE候选 from:', data.sender);
                await this.handleIceCandidate(data);
            });

            // 设置WebRTC回调
            this.socket.on('connect', () => {
                this.onIceCandidate((candidate, username) => {
                    this.socket.emit('ice_candidate', {
                        candidate: candidate,
                        target: username,
                        sender: this.roomConfig.currentUser
                    });
                });
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
    joinVoiceRoom() {
        if (this.socket) {
            this.socket.emit('join_voice_room', {
                room_id: this.roomConfig.roomId,
                username: this.roomConfig.currentUser
            });
        }
    }

    // 离开语音房间
    leaveVoiceRoom() {
        if (this.socket) {
            this.socket.emit('leave_voice_room', {
                room_id: this.roomConfig.roomId,
                username: this.roomConfig.currentUser
            });
        }
    }

    // 设置本地流
    setLocalStream(stream) {
        this.localStream = stream;
    }

    // 创建对等连接
    createPeerConnection(username, isInitiator) {
        console.log(`[DEBUG] createPeerConnection - 用户: ${username}, 是否发起者: ${isInitiator}`);
        if (this.peerConnections[username]) {
            console.log(`[DEBUG] 对等连接已存在，跳过创建 - 用户: ${username}`);
            return this.peerConnections[username];
        }

        console.log(`[DEBUG] 创建RTCPeerConnection - iceServers配置:`, iceServers);
        const pc = new RTCPeerConnection(iceServers);

        // 添加本地流
        if (this.localStream) {
            console.log(`[DEBUG] 添加本地流 - tracks数量: ${this.localStream.getTracks().length}`);
            this.localStream.getTracks().forEach(track => {
                console.log(`[DEBUG] 添加track - kind: ${track.kind}, id: ${track.id}, enabled: ${track.enabled}`);
                pc.addTrack(track, this.localStream);
            });
        }

        // 处理远程流
        pc.ontrack = (event) => {
            console.log(`[DEBUG] ontrack事件触发 - 用户: ${username}, tracks: ${event.streams[0].getTracks().length}`);
            console.log(`[DEBUG] 远程流详情:`, event.streams[0]);
            if (this.onRemoteStreamCallback) {
                this.onRemoteStreamCallback(event.streams[0], username);
            }
        };

        // 处理ICE候选
        pc.onicecandidate = (event) => {
            console.log(`[DEBUG] onicecandidate事件触发 - 用户: ${username}, candidate: ${event.candidate ? '存在' : 'null'}`);
            if (event.candidate) {
                console.log(`[DEBUG] ICE候选 - 用户: ${username}, 类型: ${event.candidate.type}, 协议: ${event.candidate.protocol}, 地址: ${event.candidate.address}`);
                if (this.onIceCandidateCallback) {
                    this.onIceCandidateCallback(event.candidate, username);
                }
            } else {
                console.log(`[DEBUG] ICE候选收集完成 - 用户: ${username}`);
            }
        };

        // ICE连接状态变化
        pc.oniceconnectionstatechange = () => {
            console.log(`[DEBUG] ICE连接状态变化 - 用户: ${username}, 状态: ${pc.iceConnectionState}`);
            if (pc.iceConnectionState === 'connected') {
                console.log(`[DEBUG] ✅ ICE连接成功 - 用户: ${username}`);
            } else if (pc.iceConnectionState === 'failed') {
                console.error(`[DEBUG] ❌ ICE连接失败 - 用户: ${username}`);
            }
        };

        // WebRTC连接状态变化
        pc.onconnectionstatechange = () => {
            console.log(`[DEBUG] WebRTC连接状态变化 - 用户: ${username}, 状态: ${pc.connectionState}`);
            if (pc.connectionState === 'connected') {
                console.log(`[DEBUG] ✅ WebRTC连接已建立 - 用户: ${username}`);
            } else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
                console.log(`[DEBUG] ❌ WebRTC连接断开或失败 - 用户: ${username}`);
            }
        };

        this.peerConnections[username] = pc;
        console.log('创建对等连接:', username);

        if (isInitiator) {
            // 创建并发送offer
            pc.createOffer().then(offer => {
                console.log('创建offer:', offer);
                return pc.setLocalDescription(offer);
            }).then(() => {
                console.log('发送offer给', username);
                this.socket.emit('webrtc_offer', {
                    sdp: pc.localDescription,
                    target: username,
                    sender: this.roomConfig.currentUser
                });
            }).catch(error => {
                console.error('创建offer失败:', error);
            });
        }

        return pc;
    }

    // 处理offer
    async handleOffer(data) {
        const { sender, sdp } = data;
        console.log(`[DEBUG] handleOffer - 发送者: ${sender}, SDP类型: ${sdp.type}`);
        const isNewConnection = !this.peerConnections[sender];
        console.log(`[DEBUG] 是否新连接: ${isNewConnection}`);
        const pc = this.peerConnections[sender] || this.createPeerConnection(sender, false);

        // 只在新建连接时添加本地流
        if (isNewConnection && this.localStream) {
            console.log(`[DEBUG] 添加本地流到PeerConnection - tracks数量: ${this.localStream.getTracks().length}`);
            this.localStream.getTracks().forEach(track => {
                pc.addTrack(track, this.localStream);
            });
        }

        // 处理远程流
        pc.ontrack = (event) => {
            console.log(`[DEBUG] ontrack事件触发 - 发送者: ${sender}, stream:`, event.streams[0]);
            if (this.onRemoteStreamCallback) {
                this.onRemoteStreamCallback(event.streams[0], sender);
            }
        };

        // 处理ICE候选
        pc.onicecandidate = (event) => {
            if (event.candidate) {
                console.log(`[DEBUG] 发送ICE候选 - 发送者: ${sender}, 类型: ${event.candidate.type}, 协议: ${event.candidate.protocol}, 地址: ${event.candidate.address}`);
                if (this.onIceCandidateCallback) {
                    this.onIceCandidateCallback(event.candidate, sender);
                }
            } else {
                console.log(`ICE候选收集完成 for ${sender}`);
            }
        };

        // ICE连接状态变化
        pc.oniceconnectionstatechange = () => {
            console.log(`ICE连接状态变化 for ${sender}:`, pc.iceConnectionState);
            if (pc.iceConnectionState === 'failed') {
                console.error(`ICE连接失败 for ${sender}`);
            }
        };

        this.peerConnections[sender] = pc;

        console.log('设置远程描述...');
        await pc.setRemoteDescription(new RTCSessionDescription(sdp));
        console.log('创建answer...');
        const answer = await pc.createAnswer();
        console.log('设置本地描述...');
        await pc.setLocalDescription(answer);

        // 添加缓存的ICE候选
        if (this.iceCandidateQueues[sender]) {
            console.log(`添加 ${sender} 的 ${this.iceCandidateQueues[sender].length} 个缓存ICE候选`);
            for (const cachedCandidate of this.iceCandidateQueues[sender]) {
                try {
                    await pc.addIceCandidate(new RTCIceCandidate(cachedCandidate));
                } catch (error) {
                    console.error(`添加缓存的ICE候选失败:`, error);
                }
            }
            delete this.iceCandidateQueues[sender];
        }

        console.log(`发送answer给 ${sender}`);
        return answer;
    }

    // 处理answer
    async handleAnswer(data) {
        const { sender, sdp } = data;
        console.log(`[DEBUG] handleAnswer - 发送者: ${sender}, SDP类型: ${sdp.type}`);
        const pc = this.peerConnections[sender];
        if (pc) {
            console.log(`[DEBUG] PeerConnection存在 - 当前signalingState: ${pc.signalingState}`);
            // 检查连接状态，避免重复设置
            if (pc.signalingState === 'stable') {
                console.log(`[DEBUG] 连接状态已为stable，跳过设置answer - 发送者: ${sender}`);
                return;
            }

            console.log(`[DEBUG] 设置远程描述 - 发送者: ${sender}`);
            await pc.setRemoteDescription(new RTCSessionDescription(sdp));
            console.log(`[DEBUG] 远程描述设置完成 - 发送者: ${sender}`);

            // 添加缓存的ICE候选
            if (this.iceCandidateQueues[sender]) {
                console.log(`[DEBUG] 添加缓存的ICE候选 - 发送者: ${sender}, 数量: ${this.iceCandidateQueues[sender].length}`);
                for (const cachedCandidate of this.iceCandidateQueues[sender]) {
                    try {
                        await pc.addIceCandidate(new RTCIceCandidate(cachedCandidate));
                        console.log(`[DEBUG] 成功添加缓存ICE候选 - 发送者: ${sender}`);
                    } catch (error) {
                        console.error(`[DEBUG] 添加缓存的ICE候选失败 - 发送者: ${sender}, 错误:`, error);
                    }
                }
                delete this.iceCandidateQueues[sender];
                console.log(`[DEBUG] 已清除ICE候选缓存 - 发送者: ${sender}`);
            }
        } else {
            console.log(`[DEBUG] 警告: 收到answer，但连接不存在 - 发送者: ${sender}`);
        }
    }

    // 处理ICE候选
    async handleIceCandidate(data) {
        const { sender, candidate } = data;
        console.log(`[DEBUG] handleIceCandidate - 发送者: ${sender}, 候选类型: ${candidate ? candidate.type : 'undefined'}, 协议: ${candidate ? candidate.protocol : 'undefined'}`);
        const pc = this.peerConnections[sender];

        if (!pc) {
            console.log(`[DEBUG] PeerConnection不存在 - 发送者: ${sender}`);
            return;
        }

        if (pc.remoteDescription) {
            try {
                await pc.addIceCandidate(new RTCIceCandidate(candidate));
                console.log(`[DEBUG] 成功添加ICE候选 - 发送者: ${sender}`);
            } catch (error) {
                console.error(`[DEBUG] 添加ICE候选失败 - 发送者: ${sender}, 错误:`, error);
            }
        } else {
            console.log(`[DEBUG] 远程描述未设置，缓存ICE候选 - 发送者: ${sender}`);
            if (!this.iceCandidateQueues[sender]) {
                this.iceCandidateQueues[sender] = [];
            }
            this.iceCandidateQueues[sender].push(candidate);
            console.log(`[DEBUG] 已缓存ICE候选 - 发送者: ${sender}, 当前缓存数量: ${this.iceCandidateQueues[sender].length}`);
        }
    }

    // 关闭对等连接
    closePeerConnection(username) {
        const pc = this.peerConnections[username];
        if (pc) {
            pc.close();
            delete this.peerConnections[username];
        }

        if (this.iceCandidateQueues[username]) {
            delete this.iceCandidateQueues[username];
        }
    }

    // 关闭所有连接
    closeAllConnections() {
        for (const username in this.peerConnections) {
            this.closePeerConnection(username);
        }
    }

    // 设置远程流回调
    onRemoteStream(callback) {
        this.onRemoteStreamCallback = callback;
    }

    // 设置ICE候选回调
    onIceCandidate(callback) {
        this.onIceCandidateCallback = callback;
    }

    // 获取ICE服务器配置
    getIceServers() {
        return iceServers;
    }
}

// 导出单例实例
const webrtcManager = new WebRTCManager();
