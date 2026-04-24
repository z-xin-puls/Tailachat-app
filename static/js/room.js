// 房间页面JavaScript
let currentTarget = '';
const selfUser = ROOM_CONFIG.currentUser;

// 动态加载脚本
let trtcLoaded = false;
let webrtcManagerLoaded = false;

function loadScript(src) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

async function loadTRTC() {
    if (!trtcLoaded) {
        await loadScript('https://cdn.jsdelivr.net/npm/trtc-sdk-v5@latest/trtc.js');
        trtcLoaded = true;
        console.log('TRTC SDK loaded');
    }
}

async function loadWebRTCManager() {
    if (!webrtcManagerLoaded) {
        await loadScript('/static/js/webrtc-manager.js');
        webrtcManagerLoaded = true;
        console.log('WebRTC Manager loaded');
    }
}

// 初始化页面
document.addEventListener('DOMContentLoaded', () => {
    initSidebars();
    initPortraitSwitch();
    applyPortraitConfig(); // 应用立绘配置
    // const particleSystem = new ParticleSystem(); // 禁用粒子效果

    // 立即建立Socket.IO连接（用于聊天）
    connectToSignalingServer();

    const input = document.getElementById('chat-input');
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            sendChat();
        }
    });
    // 移除HTTP轮询，使用WebSocket实时推送
    // fetchChat();
    // setInterval(fetchChat, 1200);

    // 更新时间显示
    updateTime();
    setInterval(updateTime, 1000);

    // 定期更新房间数据
    setInterval(() => {
        fetch(`/room-data/${ROOM_CONFIG.roomId}`)
        .then(r=>r.json())
        .then(d=>{
            document.getElementById('user-count').innerText = d.count;
            document.getElementById('user-list').innerHTML = d.members;
        });
    }, 3000);
});

// 更新时间显示
function updateTime() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const timeElement = document.getElementById('current-time');
    if (timeElement) {
        timeElement.textContent = `${hours}:${minutes}`;
    }
}

// 立绘切换功能
const portraitPaths = [
    '/static/assets/spine/static/cetsyr/cetsyr_2b.png',
    '/static/assets/spine/static/cetsyr/cetsyr_epoque.png',
    '/static/assets/spine/static/cgbird/cgbird_sightseer.png',
    '/static/assets/spine/static/halo/halo_2b.png',
    '/static/assets/spine/static/highmo/highmo_epoque.png',
    '/static/assets/spine/static/highmo/highmo_nian.png',
    '/static/assets/spine/static/kalts/kalts_2b.png',
    '/static/assets/spine/static/kalts/kalts_sale.png',
    '/static/assets/spine/static/kroos/kroos_sale.png',
    '/static/assets/spine/static/kroos/kroos_sale_spb.png',
    '/static/assets/spine/static/nymph/nymph_ambienceSynesthesia.png',
    '/static/assets/spine/static/nymph/nymph_epoque.png',
    '/static/assets/spine/static/plosis/plosis_yun.png'
];
// 缓存已加载的立绘图片
const portraitCache = {};
let currentPortraitIndex = 0;
let isEditMode = false;

// 按需加载立绘图片
function loadPortrait(index) {
    return new Promise((resolve, reject) => {
        if (portraitCache[index]) {
            resolve(portraitCache[index]);
            return;
        }
        const img = new Image();
        img.src = portraitPaths[index];
        img.onload = () => {
            portraitCache[index] = img;
            resolve(img);
        };
        img.onerror = reject;
    });
}

function initPortraitSwitch() {
    const toggleBtn = document.getElementById('toggleEditMode');
    const closeBtn = document.getElementById('closeEditMode');
    const bottomBar = document.getElementById('editBottomBar');
    const infoPanel = document.getElementById('editInfoPanel');
    const select = document.getElementById('portraitSelect');

    if (!toggleBtn || !closeBtn || !bottomBar || !infoPanel || !select) return;

    // 清空现有选项
    select.innerHTML = '';

    // 为每个立绘创建选项
    portraitPaths.forEach((portrait, index) => {
        const option = document.createElement('option');
        const fileName = portrait.split('/').pop();
        option.value = index;
        option.textContent = fileName;
        select.appendChild(option);
    });

    // 设置当前选中项
    select.value = currentPortraitIndex;

    // 监听选择变化
    select.addEventListener('change', (e) => {
        currentPortraitIndex = parseInt(e.target.value);
        updatePortrait();
        savePortraitConfig(); // 保存配置
    });

    // 打开编辑模式
    toggleBtn.addEventListener('click', () => {
        isEditMode = true;
        bottomBar.classList.add('active');
        infoPanel.classList.add('active');
        const portrait = document.querySelector('.character-portrait');
        const functionPanel = document.querySelector('.function-panel');
        if (portrait) {
            portrait.classList.add('edit-mode');
        }
        if (functionPanel) {
            functionPanel.classList.add('hidden');
        }
        initPortraitControls();
    });

    // 关闭编辑模式
    closeBtn.addEventListener('click', () => {
        isEditMode = false;
        bottomBar.classList.remove('active');
        infoPanel.classList.remove('active');
        const portrait = document.querySelector('.character-portrait');
        const functionPanel = document.querySelector('.function-panel');
        if (portrait) {
            portrait.classList.remove('edit-mode');
        }
        if (functionPanel) {
            functionPanel.classList.remove('hidden');
        }
    });

    // 初始化立绘控件
    initPortraitControls();
}

function initPortraitControls() {
    const portrait = document.querySelector('.character-portrait');
    if (!portrait) return;

    const opacitySlider = document.getElementById('portraitOpacity');
    const infoX = document.getElementById('portraitInfoX');
    const infoY = document.getElementById('portraitInfoY');
    const infoWidth = document.getElementById('portraitInfoWidth');
    const infoHeight = document.getElementById('portraitInfoHeight');

    if (!opacitySlider || !infoX || !infoY || !infoWidth || !infoHeight) return;

    // 设置透明度滑块值
    const currentOpacity = (parseFloat(portrait.style.opacity) || 0.9) * 100;
    opacitySlider.value = currentOpacity;

    // 更新信息显示
    function updatePortraitInfo() {
        const currentTransform = window.getComputedStyle(portrait).transform;
        let translateX = 0, translateY = 0;
        if (currentTransform && currentTransform !== 'none') {
            const matrix = currentTransform.split(',').map(parseFloat);
            translateX = matrix[4] || 0;
            translateY = matrix[5] || 0;
        }
        const width = parseFloat(portrait.style.width) || 150;
        const height = parseFloat(portrait.style.height) || 150;

        infoX.textContent = `${Math.round(translateX)}px`;
        infoY.textContent = `${Math.round(translateY)}px`;
        infoWidth.textContent = `${Math.round(width)}%`;
        infoHeight.textContent = `${Math.round(height)}%`;
    }

    // 初始化信息显示
    updatePortraitInfo();

    // 监听透明度滑块变化
    opacitySlider.addEventListener('input', (e) => {
        portrait.style.opacity = e.target.value / 100;
        savePortraitConfig(); // 保存配置
    });

    // 实现拖拽功能
    let isDragging = false;
    let startX, startY, startTranslateX, startTranslateY;
    let animationFrameId;

    portrait.addEventListener('mousedown', (e) => {
        if (!isEditMode) return;
        isDragging = true;
        portrait.classList.add('dragging');
        startX = e.clientX;
        startY = e.clientY;

        // 获取当前的transform值
        const currentTransform = window.getComputedStyle(portrait).transform;
        if (currentTransform && currentTransform !== 'none') {
            const matrix = currentTransform.split(',').map(parseFloat);
            startTranslateX = matrix[4] || 0;
            startTranslateY = matrix[5] || 0;
        } else {
            startTranslateX = 0;
            startTranslateY = 0;
        }

        e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging || !isEditMode) return;

        if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
        }

        animationFrameId = requestAnimationFrame(() => {
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;

            const newTranslateX = startTranslateX + dx;
            const newTranslateY = startTranslateY + dy;

            portrait.style.transform = `translate(${newTranslateX}px, ${newTranslateY}px)`;
            updatePortraitInfo();
        });
    });

    document.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            portrait.classList.remove('dragging');
            if (animationFrameId) {
                cancelAnimationFrame(animationFrameId);
            }
            savePortraitConfig(); // 保存配置
        }
    });

    // 实现滚轮缩放功能
    let wheelAnimationFrameId;
    let wheelTimeoutId;

    portrait.addEventListener('wheel', (e) => {
        if (!isEditMode) return;
        e.preventDefault();

        if (wheelAnimationFrameId) {
            cancelAnimationFrame(wheelAnimationFrameId);
        }

        wheelAnimationFrameId = requestAnimationFrame(() => {
            const scaleFactor = e.deltaY > 0 ? 0.98 : 1.02;

            const currentWidth = parseFloat(portrait.style.width) || 150;
            const currentHeight = parseFloat(portrait.style.height) || 150;

            const newWidth = Math.max(50, Math.min(300, currentWidth * scaleFactor));
            const newHeight = Math.max(50, Math.min(300, currentHeight * scaleFactor));

            portrait.style.width = `${newWidth}%`;
            portrait.style.height = `${newHeight}%`;
            updatePortraitInfo();

            // 延迟保存，避免频繁请求
            clearTimeout(wheelTimeoutId);
            wheelTimeoutId = setTimeout(() => {
                savePortraitConfig();
            }, 500);
        });
    });
}

async function updatePortrait() {
    const portrait = document.querySelector('.character-portrait');
    if (portrait) {
        // 保存当前的transform值
        const currentTransform = portrait.style.transform;

        // 按需加载立绘图片
        await loadPortrait(currentPortraitIndex);
        portrait.style.backgroundImage = `url('${portraitPaths[currentPortraitIndex]}')`;

        // 恢复transform值，保持位置不变
        portrait.style.transform = currentTransform;
    }
}

// 应用立绘配置
async function applyPortraitConfig() {
    const portrait = document.querySelector('.character-portrait');
    if (!portrait || !PORTRAIT_CONFIG) return;

    // 先隐藏立绘，避免闪烁
    portrait.style.opacity = '0';

    // 应用立绘索引
    currentPortraitIndex = PORTRAIT_CONFIG.portrait_index || 0;
    await loadPortrait(currentPortraitIndex);
    portrait.style.backgroundImage = `url('${portraitPaths[currentPortraitIndex]}')`;

    // 应用位置（使用绝对像素值）
    const posX = PORTRAIT_CONFIG.position_x || 0;
    const posY = PORTRAIT_CONFIG.position_y || 0;
    portrait.style.transform = `translate(${posX}px, ${posY}px)`;

    // 应用缩放
    const scale = PORTRAIT_CONFIG.portrait_scale || 1.0;
    const baseSize = 150;
    portrait.style.width = `${baseSize * scale}%`;
    portrait.style.height = `${baseSize * scale}%`;

    // 更新选择器值
    const select = document.getElementById('portraitSelect');
    if (select) {
        select.value = currentPortraitIndex;
    }

    // 更新透明度滑块
    const opacity = PORTRAIT_CONFIG.opacity || 90;
    const opacitySlider = document.getElementById('portraitOpacity');
    if (opacitySlider) {
        opacitySlider.value = opacity;
    }

    // 最后显示立绘
    portrait.style.opacity = opacity / 100;

    console.log('立绘配置已应用:', PORTRAIT_CONFIG);
}

// 保存立绘配置
async function savePortraitConfig() {
    const portrait = document.querySelector('.character-portrait');
    if (!portrait) return;

    // 获取当前配置
    const transform = window.getComputedStyle(portrait).transform;
    let posX = 0, posY = 0;
    if (transform && transform !== 'none') {
        const matrix = transform.split(',').map(parseFloat);
        posX = matrix[4] || 0;
        posY = matrix[5] || 0;
    }

    const width = parseFloat(portrait.style.width) || 150;
    const height = parseFloat(portrait.style.height) || 150;
    const scale = width / 150; // 基于宽度计算缩放比例
    const opacity = (parseFloat(portrait.style.opacity) || 0.9) * 100;

    const config = {
        portrait_index: currentPortraitIndex,
        position_x: posX,
        position_y: posY,
        portrait_scale: scale,
        opacity: opacity
    };

    try {
        const response = await fetch(`/api/room/${ROOM_CONFIG.roomId}/portrait`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        const result = await response.json();
        if (result.success) {
            console.log('立绘配置已保存:', config);
        } else {
            console.error('保存立绘配置失败:', result.error);
        }
    } catch (error) {
        console.error('保存立绘配置失败:', error);
    }
}

// 侧边栏功能
function initSidebars() {
    const sidebarLeft = document.getElementById('sidebarLeft');
    const sidebarRight = document.getElementById('sidebarRight');
    const leftToggle = document.getElementById('sidebarLeftToggle');
    const rightToggle = document.getElementById('sidebarRightToggle');

    // 左侧边栏切换
    leftToggle.addEventListener('click', function(e) {
        e.stopPropagation();
        sidebarLeft.classList.toggle('active');
        // 关闭右侧边栏
        sidebarRight.classList.remove('active');
    });

    // 右侧边栏切换
    rightToggle.addEventListener('click', function(e) {
        e.stopPropagation();
        sidebarRight.classList.toggle('active');
        // 关闭左侧边栏
        sidebarLeft.classList.remove('active');
    });

    // 点击外部收起侧边栏
    document.addEventListener('click', function(e) {
        if (!sidebarLeft.contains(e.target) && !leftToggle.contains(e.target)) {
            sidebarLeft.classList.remove('active');
        }
        if (!sidebarRight.contains(e.target) && !rightToggle.contains(e.target)) {
            sidebarRight.classList.remove('active');
        }
    });
}

// 音量控制面板
function openVolumePanel(u) {
    currentTarget = u || '';
    document.getElementById('vol-target').innerText = currentTarget || '-';
    document.getElementById('vol-backdrop').style.display = 'block';

    const micKey = 'micGain';
    const playKey = 'playGain:' + currentTarget;
    const micVal = parseInt(localStorage.getItem(micKey) || '100', 10);
    const playVal = parseInt(localStorage.getItem(playKey) || '100', 10);

    const micSlider = document.getElementById('mic-slider');
    const playSlider = document.getElementById('play-slider');
    const playHint = document.getElementById('play-hint');
    micSlider.value = String(isNaN(micVal) ? 100 : micVal);
    playSlider.value = String(isNaN(playVal) ? 100 : playVal);
    document.getElementById('mic-val').innerText = micSlider.value + '%';
    document.getElementById('play-val').innerText = playSlider.value + '%';

    if (currentTarget === selfUser) {
        playSlider.classList.add('disabled');
        playSlider.disabled = true;
        playHint.innerText = '提示：点击其他成员后可调节"听到TA的音量"。';
    } else {
        playSlider.classList.remove('disabled');
        playSlider.disabled = false;
        playHint.innerText = '';
    }

    applyMicGain();
    applyPlaybackGain();
}

function closeVolumePanel() {
    document.getElementById('vol-backdrop').style.display = 'none';
}

function applyMicGain() {
    const micSlider = document.getElementById('mic-slider');
    const val = parseInt(micSlider.value, 10);
    document.getElementById('mic-val').innerText = val + '%';
    localStorage.setItem('micGain', String(val));
    // 音量控制现在在浏览器端本地处理，不需要后端API
}

function applyPlaybackGain() {
    if (!currentTarget || currentTarget === selfUser) {
        return;
    }
    const playSlider = document.getElementById('play-slider');
    const val = parseInt(playSlider.value, 10);
    document.getElementById('play-val').innerText = val + '%';
    localStorage.setItem('playGain:' + currentTarget, String(val));
    // 音量控制现在在浏览器端本地处理，不需要后端API
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('mic-slider').addEventListener('input', applyMicGain);
    document.getElementById('play-slider').addEventListener('input', applyPlaybackGain);
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeVolumePanel();
    }
});

// WebRTC语音通话
let localStream = null;
let voiceEnabled = false;

// 连接Socket.IO服务器
async function connectToSignalingServer() {
    // 确保webrtc-manager.js已加载
    if (typeof webrtcManager === 'undefined') {
        await loadWebRTCManager();
    }
    webrtcManager.setRoomConfig(ROOM_CONFIG);
    webrtcManager.connectToSignalingServer();

    // 设置聊天回调
    webrtcManager.onChatHistory((data) => {
        console.log('收到聊天历史:', data.messages);
        const msgs = data.messages || [];
        for (const m of msgs) {
            appendChat(m);
            if (m.id && m.id > lastChatId) lastChatId = m.id;
        }
    });

    webrtcManager.onChatMessage((data) => {
        console.log('收到聊天消息:', data);
        appendChat(data);
        if (data.id && data.id > lastChatId) lastChatId = data.id;
    });

    webrtcManager.onChatError((data) => {
        console.error('聊天错误:', data.error);
        alert('发送失败：' + (data.error || '未知错误'));
    });

    // 设置WebRTC回调
    webrtcManager.onRemoteStream((stream, username) => {
        playRemoteStream(stream);
    });
}

// 创建对等连接
async function createPeerConnection(username, isInitiator) {
    webrtcManager.setLocalStream(localStream);
    webrtcManager.createPeerConnection(username, isInitiator);
}

// 处理offer（webrtc-manager已处理）
async function handleOffer(data) {
    // 已移至webrtc-manager.js
}

// 处理answer（webrtc-manager已处理）
async function handleAnswer(data) {
    // 已移至webrtc-manager.js
}

// 处理ICE候选（webrtc-manager已处理）
async function handleIceCandidate(data) {
    // 已移至webrtc-manager.js
}

// 播放远程流
function playRemoteStream(stream) {
    const audioElements = document.querySelectorAll('.remote-audio');
    for (const audio of audioElements) {
        if (audio.srcObject === stream) {
            return;
        }
    }

    const audio = new Audio();
    audio.srcObject = stream;

    // ============ 修复卡顿的关键代码 ============
    audio.autoplay = true;
    audio.playsInline = true;         // 必须加
    audio.muted = false;              // 必须加
    audio.preload = 'auto';           // 改成 auto，不要 metadata
    audio.defaultMuted = false;

    // 强制激活音频（解决浏览器休眠导致的卡顿）
    audio.oncanplay = () => {
        audio.play().catch(err => console.warn('音频自动播放需用户交互:', err));
    };

    audio.className = 'remote-audio';
    document.body.appendChild(audio);
}

// 显示通知
function showNotification(message) {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #4CAF50;
        color: white;
        padding: 12px 24px;
        border-radius: 4px;
        z-index: 10000;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);

    // 3秒后自动消失
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// 关闭对等连接
function closePeerConnection(username) {
    webrtcManager.closePeerConnection(username);

    // 移除对应的音频元素
    const audioElements = document.querySelectorAll('.remote-audio');
    audioElements.forEach(audio => {
        if (audio.srcObject) {
            audio.srcObject.getTracks().forEach(track => track.stop());
            audio.remove();
        }
    });
}

// 启动语音
async function startVoiceClient() {
    try {
        // 动态加载TRTC SDK和WebRTC Manager
        await loadTRTC();
        await loadWebRTCManager();

        console.log('开始获取音频流...');
        // 获取本地音频流 - 优化参数减少回声
        localStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: false,    // 关闭自动增益减少回声
                sampleRate: 16000,         // 降低采样率减少回声
                channelCount: 1,
                latency: 0.05,            // 增加延迟减少回声
                echoCancellationType: 'browser',
                suppressLocalAudioPlayback: true  // 抑制本地音频回放
            },
            video: false
        });

        console.log('音频流获取成功，tracks:', localStream.getTracks().length);
        voiceEnabled = true;
        webrtcManager.setVoiceEnabled(true);
        webrtcManager.setLocalStream(localStream);

        // 加入语音房间
        console.log('加入语音房间...');
        webrtcManager.joinVoiceRoom();

        // 显示会议通话开启提示
        showNotification('语音通话已开启');

        // 强制浏览器不休眠音频（超级关键）
        document.body.addEventListener('click', () => {
            console.log('强制激活所有远程音频...');
            document.querySelectorAll('.remote-audio').forEach(a => a.play());
        }, { once: true });

        updateVoiceButton(true);
    } catch (error) {
        console.error('获取音频流失败:', error);
        alert('无法访问麦克风，请检查权限设置');
    }
}

// 停止语音
function stopVoiceClient() {
    voiceEnabled = false;
    webrtcManager.setVoiceEnabled(false);

    // 关闭所有对等连接
    webrtcManager.closeAllConnections();

    // 停止本地流
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        localStream = null;
    }

    // 清理所有远程音频元素
    document.querySelectorAll('.remote-audio').forEach(audio => {
        if (audio.srcObject) {
            audio.srcObject.getTracks().forEach(track => track.stop());
        }
        audio.remove();
    });

    // 离开语音房间
    webrtcManager.leaveVoiceRoom();

    // 显示会议通话关闭提示
    showNotification('语音通话已结束');

    updateVoiceButton(false);
}

// 切换语音
function toggleVoice() {
    if (voiceEnabled) {
        stopVoiceClient();
    } else {
        startVoiceClient();
    }
}

// 更新语音按钮状态
function updateVoiceButton(enabled) {
    const btn = document.getElementById('voiceToggleBtn');
    const icon = document.getElementById('voiceBtnIcon');
    const text = document.getElementById('voiceBtnText');

    if (enabled) {
        icon.textContent = '⏹';
        text.textContent = '关闭语音';
        btn.classList.remove('terminal-btn-primary');
        btn.classList.add('terminal-btn-danger');
    } else {
        icon.textContent = '▶';
        text.textContent = '启动语音';
        btn.classList.remove('terminal-btn-danger');
        btn.classList.add('terminal-btn-primary');
    }
}

// 聊天功能
let lastChatId = 0;

function appendChat(m) {
    const box = document.getElementById('chat-box');
    const line = document.createElement('div');
    line.className = 'chat-line';
    const t = document.createElement('div');
    t.className = 'chat-time';
    t.textContent = m.time || '';
    const u = document.createElement('div');
    u.className = 'chat-user';
    u.textContent = m.user || '';
    const text = document.createElement('div');
    text.className = 'chat-text';
    text.textContent = m.text || '';
    line.appendChild(t);
    line.appendChild(u);
    line.appendChild(text);
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
}

function fetchChat() {
    // Socket.IO版本：不再需要HTTP轮询
    // 消息通过Socket.IO实时推送
}

function sendChat() {
    const input = document.getElementById('chat-input');
    const text = (input.value || '').trim();
    if (!text) return;

    // 使用webrtcManager发送消息
    webrtcManager.sendChat({
        room_id: ROOM_CONFIG.roomId,
        username: ROOM_CONFIG.currentUser,
        text: text
    });
    input.value = '';
}

// 加入聊天房间
function joinChatRoom() {
    // webrtc-manager已自动处理
}

// 粒子系统
class ParticleSystem {
    constructor() {
        this.canvas = document.getElementById('particleCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.mouseX = -1000;
        this.mouseY = -1000;
        this.config = {
            particleSize: 2,
            particleMargin: 2,
            repulsionRadius: 105,
            repulsionForce: 1.2,
            friction: 0.15,
            returnSpeed: 0.02,
            maxDisplayRatio: 0.8,
            samplingStep: 5,
            mobileRepulsionRadius: 78
        };
        this.isMobile = window.innerWidth <= 768;
        this.init();
    }
    
    init() {
        console.log('初始化粒子系统...');
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
        document.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        document.addEventListener('touchmove', (e) => this.handleTouchMove(e));
        
        // 测试Canvas是否工作
        this.ctx.fillStyle = 'red';
        this.ctx.fillRect(50, 50, 100, 100);
        console.log('Canvas测试矩形已绘制');
        
        // 先创建一些随机粒子作为备用
        this.createRandomParticles();
        console.log(`创建了 ${this.particles.length} 个随机粒子`);
        
        // 启动动画
        this.animate();
        console.log('动画已启动');
        
        // 然后尝试加载图片
        this.loadImageAndCreateParticles();
    }
    
    resizeCanvas() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }
    
    handleMouseMove(e) {
        this.mouseX = e.clientX;
        this.mouseY = e.clientY;
    }
    
    handleTouchMove(e) {
        if (e.touches.length > 0) {
            this.mouseX = e.touches[0].clientX;
            this.mouseY = e.touches[0].clientY;
        }
    }
    
    loadImageAndCreateParticles() {
        console.log('开始加载图片并创建粒子...');
        const img = new Image();
        img.src = '/static/images/img/Yan.png';
        console.log('图片路径:', img.src);
        
        img.onload = () => {
            console.log('图片加载成功，图片尺寸:', img.width, 'x', img.height);
            console.log('清空现有粒子并创建新粒子...');
            this.particles = []; // 清空现有粒子
            this.createParticlesFromImage(img);
            console.log(`从图片创建了 ${this.particles.length} 个粒子`);
        };
        img.onerror = (error) => {
            console.log('图片加载失败，错误:', error);
            console.log('保持使用随机粒子');
            // 保持现有的随机粒子
        };
    }
    
    createParticlesFromImage(img) {
        console.log('开始从图片创建粒子...');
        const tempCanvas = document.createElement('canvas');
        const tempCtx = tempCanvas.getContext('2d');
        
        const canvasWidth = window.innerWidth;
        const canvasHeight = window.innerHeight;
        const maxDisplayWidth = canvasWidth * this.config.maxDisplayRatio;
        const maxDisplayHeight = canvasHeight * this.config.maxDisplayRatio;
        
        let width = img.width;
        let height = img.height;
        console.log('原始图片尺寸:', width, 'x', height);
        
        if (width > maxDisplayWidth || height > maxDisplayHeight) {
            const ratio = Math.min(maxDisplayWidth / width, maxDisplayHeight / height);
            width *= ratio;
            height *= ratio;
            console.log('调整后尺寸:', width, 'x', height, '比例:', ratio);
        }
        
        tempCanvas.width = width;
        tempCanvas.height = height;
        tempCtx.drawImage(img, 0, 0, width, height);
        
        const imgData = tempCtx.getImageData(0, 0, width, height);
        console.log('获取图像数据，尺寸:', imgData.width, 'x', imgData.height);
        
        const offsetX = (canvasWidth - width) / 2;
        const offsetY = (canvasHeight - height) / 2;
        console.log('偏移量:', offsetX, offsetY);
        
        let particleCount = 0;
        for (let y = 0; y < height; y += this.config.samplingStep) {
            for (let x = 0; x < width; x += this.config.samplingStep) {
                const alpha = imgData.data[(y * width + x) * 4 + 3];
                if (alpha > 64) {
                    const brightness = this.getPixelBrightness(imgData, x, y);
                    const particle = new Particle(
                        x + offsetX,
                        y + offsetY,
                        this.config,
                        brightness > 128 ? 'light' : 'dark'
                    );
                    this.particles.push(particle);
                    particleCount++;
                }
            }
        }
        console.log(`从图片创建了 ${particleCount} 个粒子`);
    }
    
    createRandomParticles() {
        const particleCount = 200;
        for (let i = 0; i < particleCount; i++) {
            const x = Math.random() * window.innerWidth;
            const y = Math.random() * window.innerHeight;
            this.particles.push(new Particle(x, y, this.config, 'light'));
        }
    }
    
    getPixelBrightness(imgData, x, y) {
        const i = (y * imgData.width + x) * 4;
        return (imgData.data[i] + imgData.data[i + 1] + imgData.data[i + 2]) / 3;
    }
    
    animate() {
        // 清除画布
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // 绘制所有粒子
        this.particles.forEach(particle => {
            particle.update(this.mouseX, this.mouseY, this.isMobile);
            particle.draw(this.ctx);
        });
        
        // 调试：每60帧输出一次
        if (!this.frameCount) this.frameCount = 0;
        this.frameCount++;
        if (this.frameCount % 60 === 0) {
            console.log(`动画运行中，当前粒子数: ${this.particles.length}`);
        }
        
        // 继续动画循环
        requestAnimationFrame(() => this.animate());
    }
}

class Particle {
    constructor(x, y, config, colorType) {
        this.x = x;
        this.y = y;
        this.originalX = x;
        this.originalY = y;
        this.vx = 0;
        this.vy = 0;
        this.config = config;
        this.colorType = colorType;
        this.opacity = Math.random() * 0.4 + 0.4;
    }
    
    update(mouseX, mouseY, isMobile) {
        const dx = this.x - mouseX;
        const dy = this.y - mouseY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        const repulsionRadius = isMobile ? this.config.mobileRepulsionRadius : this.config.repulsionRadius;
        
        if (distance < repulsionRadius) {
            const angle = Math.atan2(dy, dx);
            const ratio = (repulsionRadius - distance) / repulsionRadius;
            const force = ratio * ratio * this.config.repulsionForce;
            
            this.vx += Math.cos(angle) * force;
            this.vy += Math.sin(angle) * force;
        }
        
        const returnX = (this.originalX - this.x) * this.config.returnSpeed;
        const returnY = (this.originalY - this.y) * this.config.returnSpeed;
        this.vx += returnX;
        this.vy += returnY;
        
        this.vx *= (1 - this.config.friction);
        this.vy *= (1 - this.config.friction);
        
        this.x += this.vx;
        this.y += this.vy;
    }
    
    draw(ctx) {
        const color = this.colorType === 'light' ? 
            `rgba(45, 212, 191, ${this.opacity})` : 
            `rgba(139, 92, 246, ${this.opacity})`;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.config.particleSize, 0, Math.PI * 2);
        ctx.fill();
        
        // 调试：每100个粒子输出一次位置信息
        if (Math.random() < 0.01) {
            console.log(`粒子位置: (${Math.round(this.x)}, ${Math.round(this.y)}), 颜色: ${this.colorType}, 透明度: ${this.opacity}`);
        }
    }
}
