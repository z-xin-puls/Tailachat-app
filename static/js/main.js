// 主页JavaScript
// 数据将从模板中的全局变量获取

// 地图拖动功能
var isDragging = false;
var startX = 0, startY = 0;
var mapX = 0, mapY = 0;
var hasMoved = false;
var scale = 1;
var mapContainer = document.getElementById('mapContainer');
var map = document.getElementById('map');

function centerMap() {
    mapX = (window.innerWidth - 4081 * scale) / 2;
    mapY = (window.innerHeight - 5488 * scale) / 2;
    updateMapPosition();
}

function updateMapPosition() {
    // 计算地图的实际尺寸（考虑缩放）
    var mapWidth = 4081 * scale;
    var mapHeight = 5488 * scale;
    var containerWidth = window.innerWidth;
    var containerHeight = window.innerHeight;
    
    // 计算边界限制
    var minX, minY, maxX, maxY;
    
    if (mapWidth <= containerWidth) {
        // 地图宽度小于等于容器宽度时，水平居中
        minX = (containerWidth - mapWidth) / 2;
        maxX = minX;
        mapX = minX; // 强制居中
    } else {
        // 地图宽度大于容器宽度时，允许拖动
        minX = containerWidth - mapWidth; // 负数，允许向左拖动
        maxX = 0; // 正数，允许向右拖动
        mapX = Math.max(minX, Math.min(maxX, mapX));
    }
    
    if (mapHeight <= containerHeight) {
        // 地图高度小于等于容器高度时，垂直居中
        minY = (containerHeight - mapHeight) / 2;
        maxY = minY;
        mapY = minY; // 强制居中
    } else {
        // 地图高度大于容器高度时，允许拖动
        minY = containerHeight - mapHeight;
        maxY = 0;
        mapY = Math.max(minY, Math.min(maxY, mapY));
    }
    
    map.style.left = mapX + 'px';
    map.style.top = mapY + 'px';
    map.style.transform = 'scale(' + scale + ')';
    map.style.transformOrigin = '0 0';
    updateZoomLevel();
}

function updateZoomLevel() {
    document.getElementById('zoomLevel').innerText = Math.round(scale * 100) + '%';
}

function zoomIn() {
    if (scale < 3) {
        scale += 0.2;
        updateMapPosition();
    }
}

function zoomOut() {
    if (scale > 0.3) {
        scale -= 0.2;
        updateMapPosition();
    }
}

function resetZoom() {
    scale = 1;
    updateMapPosition();
}

// 鼠标滚轮缩放
mapContainer.addEventListener('wheel', function(e) {
    e.preventDefault();
    var delta = e.deltaY > 0 ? -0.1 : 0.1;
    var newScale = scale + delta;
    
    if (newScale >= 0.3 && newScale <= 3) {
        // 获取鼠标在地图上的位置
        var rect = map.getBoundingClientRect();
        var mouseX = e.clientX - rect.left;
        var mouseY = e.clientY - rect.top;
        
        // 计算缩放前鼠标在地图上的相对位置
        var relativeX = mouseX / scale;
        var relativeY = mouseY / scale;
        
        scale = newScale;
        
        // 调整地图位置，使鼠标位置保持不变
        mapX -= (relativeX * scale - mouseX);
        mapY -= (relativeY * scale - mouseY);
        
        updateMapPosition();
    }
});

// 拖动事件
mapContainer.addEventListener('mousedown', function(e) {
    if (e.target.classList.contains('outpost')) return;
    if (e.target.closest('.create-modal, .modal-overlay, .topbar')) return;
    
    isDragging = true;
    hasMoved = false;
    startX = e.clientX - mapX;
    startY = e.clientY - mapY;
    e.preventDefault();
});

document.addEventListener('mousemove', function(e) {
    if (!isDragging) return;
    hasMoved = true;
    mapX = e.clientX - startX;
    mapY = e.clientY - startY;
    updateMapPosition();
});

document.addEventListener('mouseup', function() {
    isDragging = false;
    // 延迟重置hasMoved，避免click事件立即触发
    setTimeout(function() {
        hasMoved = false;
    }, 10);
});

// 地图点击功能已移除，房间创建改为在据点弹窗中进行

function openCreateModal() {
    document.getElementById('modalOverlay').style.display = 'block';
    document.getElementById('createModal').style.display = 'block';
}

function closeCreateModal() {
    document.getElementById('modalOverlay').style.display = 'none';
    document.getElementById('createModal').style.display = 'none';
    document.getElementById('createForm').reset();
}

// 据点创建房间表单提交
document.getElementById('fortressCreateForm').addEventListener('submit', function(e) {
    e.preventDefault();
    var formData = new FormData(e.target);
    
    fetch('/create_fortress_room', {
        method: 'POST',
        body: formData
    })
    .then(response => response.text())
    .then(data => {
        if (data === 'success') {
            // 重新加载据点房间列表
            const fortressId = document.getElementById('fortressId').value;
            loadFortressRooms(fortressId);
            // 清空表单
            e.target.reset();
            // 显示成功提示
            const roomList = document.getElementById('fortressRoomList');
            const successMsg = document.createElement('div');
            successMsg.style.cssText = 'color: #10b981; text-align: center; padding: 10px; margin-bottom: 10px; font-size: 12px;';
            successMsg.textContent = '✅ 房间创建成功！';
            roomList.parentNode.insertBefore(successMsg, roomList);
            setTimeout(() => successMsg.remove(), 3000);
        } else {
            alert('创建房间失败：' + data);
        }
    })
    .catch(error => {
        console.error('创建房间失败:', error);
        alert('创建房间失败，请重试');
    });
});

document.getElementById('createForm').addEventListener('submit', function(e) {
    e.preventDefault();
    var formData = new FormData(e.target);
    
    fetch('/create_with_location', {
        method: 'POST',
        body: formData
    }).then(function(response) {
        if (response.ok) {
            closeCreateModal();
            window.location.reload();
        }
    });
});

// 渲染据点系统
function renderFortresses() {
    var mapElement = document.getElementById('map');
    
    fortresses.forEach(function(fortress) {
        // 直接使用数据库中的像素坐标和半径
        var x = fortress.x;
        var y = fortress.y;
        var radius = fortress.radius;
        
        console.log(`渲染据点 ${fortress.name}: 坐标(${x}px, ${y}px), 半径${radius}px`);
        
        // 创建据点呼吸光环
        var fortressRing = document.createElement('div');
        fortressRing.className = 'fortress-ring';
        fortressRing.style.position = 'absolute';
        fortressRing.style.left = x + 'px';
        fortressRing.style.top = y + 'px';
        fortressRing.style.transform = 'translate(-50%, -50%)';
        fortressRing.style.pointerEvents = 'none';
        fortressRing.style.zIndex = '2';
        
        // 根据据点大小决定光环类型
        if (radius >= 500) {
            fortressRing.classList.add('fortress-ring-large');
        } else if (radius >= 200) {
            fortressRing.classList.add('fortress-ring-medium');
        } else {
            fortressRing.classList.add('fortress-ring-small');
        }
        
        // 创建多层立体光环
        var ringOuter = document.createElement('div');
        ringOuter.className = 'fortress-ring-layer fortress-ring-outer';
        ringOuter.style.left = '50%';
        ringOuter.style.top = '50%';
        ringOuter.style.transform = 'translate(-50%, -50%)';
        ringOuter.style.borderColor = 'rgba(255, 255, 255, 0.6)';
        ringOuter.style.boxShadow = '0 0 20px rgba(255, 255, 255, 0.8), 0 0 40px rgba(255, 255, 255, 0.4)';
        
        var ringMiddle = document.createElement('div');
        ringMiddle.className = 'fortress-ring-layer fortress-ring-middle';
        ringMiddle.style.left = '50%';
        ringMiddle.style.top = '50%';
        ringMiddle.style.transform = 'translate(-50%, -50%)';
        ringMiddle.style.borderColor = '#ffffff';
        ringMiddle.style.boxShadow = '0 0 15px rgba(255, 255, 255, 1), 0 0 30px rgba(255, 255, 255, 0.8)';
        
        var ringInner = document.createElement('div');
        ringInner.className = 'fortress-ring-layer fortress-ring-inner';
        ringInner.style.left = '50%';
        ringInner.style.top = '50%';
        ringInner.style.transform = 'translate(-50%, -50%)';
        ringInner.style.borderColor = 'rgba(255, 255, 255, 0.9)';
        ringInner.style.boxShadow = '0 0 10px rgba(255, 255, 255, 1), 0 0 20px rgba(255, 255, 255, 0.8)';
        
        // 组装多层光环
        fortressRing.appendChild(ringOuter);
        fortressRing.appendChild(ringMiddle);
        fortressRing.appendChild(ringInner);
        
        // 创建据点中心点
        var fortressCenter = document.createElement('div');
        fortressCenter.className = 'fortress-center';
        fortressCenter.style.position = 'absolute';
        fortressCenter.style.left = x + 'px';
        fortressCenter.style.top = y + 'px';
        fortressCenter.style.transform = 'translate(-50%, -50%)';
        fortressCenter.style.width = '20px';
        fortressCenter.style.height = '20px';
        fortressCenter.style.borderRadius = '50%';
        fortressCenter.style.background = fortress.color;
        fortressCenter.style.border = '3px solid #fff';
        fortressCenter.style.cursor = 'pointer';
        fortressCenter.style.zIndex = '5';
        fortressCenter.onclick = function() {
            showFortressInfo(fortress);
        };
        
        // 创建据点标签 - 使用像素坐标
        var fortressLabel = document.createElement('div');
        fortressLabel.className = 'fortress-label';
        fortressLabel.style.position = 'absolute';
        fortressLabel.style.left = x + 'px';
        fortressLabel.style.top = (y + radius + 20) + 'px'; // 像素偏移
        fortressLabel.style.transform = 'translateX(-50%)';
        fortressLabel.style.color = fortress.color;
        fortressLabel.style.fontSize = '12px';
        fortressLabel.style.fontWeight = '700';
        fortressLabel.style.textShadow = '0 0 5px rgba(0,0,0,0.8)';
        fortressLabel.style.pointerEvents = 'none';
        fortressLabel.style.zIndex = '4';
        fortressLabel.textContent = fortress.name;
        
        mapElement.appendChild(fortressRing);
        mapElement.appendChild(fortressCenter);
        mapElement.appendChild(fortressLabel);
    });
}

// 显示据点信息
function showFortressInfo(fortress) {
    document.getElementById('roomInfoName').textContent = fortress.name;
    document.getElementById('roomInfoDetails').innerHTML = 
        '<div>据点ID：' + fortress.id + '</div>' +
        '<div>位置：(' + fortress.x + ', ' + fortress.y + ')</div>' +
        '<div>半径：' + fortress.radius + '</div>' +
        '<div>描述：' + (fortress.description || '无描述') + '</div>';
    
    // 设置创建房间表单的隐藏字段
    document.getElementById('fortressId').value = fortress.id;
    
    // 加载据点房间列表
    loadFortressRooms(fortress.id);
    
    document.getElementById('roomInfoOverlay').style.display = 'block';
    document.getElementById('roomInfoModal').style.display = 'block';
    
    // 启动据点弹窗粒子系统，传入据点图片路径
    if (modalParticleSystem) {
        setTimeout(() => {
            var imagePath = fortress.image || '/static/images/img/Yan.png';
            modalParticleSystem.init(imagePath);
        }, 100);
    }
}

// 加载据点房间列表
function loadFortressRooms(fortressId) {
    fetch('/api/fortress_rooms/' + fortressId)
        .then(response => response.json())
        .then(data => {
            const roomList = document.getElementById('fortressRoomList');
            roomList.innerHTML = '';
            
            if (data.rooms && data.rooms.length > 0) {
                data.rooms.forEach(room => {
                    const roomItem = document.createElement('div');
                    roomItem.style.cssText = 'background: #111827; border: 1px solid #374151; border-radius: 6px; padding: 10px; margin-bottom: 8px; cursor: pointer; transition: all 0.2s ease;';
                    roomItem.innerHTML = 
                        '<div style="color: #fff; font-weight: bold; font-size: 13px; margin-bottom: 4px;">🏠 ' + room.name + '</div>' +
                        '<div style="color: #cbd5e1; font-size: 11px;">房主：' + room.owner + ' | 在线：' + (room.online_count || 0) + '人</div>';
                    
                    roomItem.onclick = function() {
                        closeRoomInfoModal();
                        window.location.href = '/room/' + room.id;
                    };
                    
                    roomItem.onmouseover = function() {
                        this.style.background = '#374151';
                        this.style.borderColor = '#2dd4bf';
                    };
                    
                    roomItem.onmouseout = function() {
                        this.style.background = '#111827';
                        this.style.borderColor = '#374151';
                    };
                    
                    roomList.appendChild(roomItem);
                });
            } else {
                roomList.innerHTML = '<div style="color: #9ca3af; text-align: center; padding: 20px; font-size: 12px;">此据点暂无房间</div>';
            }
        })
        .catch(error => {
            console.error('加载据点房间失败:', error);
            document.getElementById('fortressRoomList').innerHTML = '<div style="color: #ef4444; text-align: center; padding: 20px; font-size: 12px;">加载失败</div>';
        });
}

// 房间信息弹窗函数
function showRoomInfoModal(room) {
    document.getElementById('roomInfoName').textContent = room.name;
    document.getElementById('roomInfoDetails').innerHTML = 
        '<div>房主：' + room.owner + '</div>' +
        '<div>房间ID：' + room.id + '</div>';
    
    document.getElementById('joinRoomBtn').onclick = function() {
        window.location.href = '/room/' + room.id;
    };
    
    document.getElementById('roomInfoOverlay').style.display = 'block';
    document.getElementById('roomInfoModal').style.display = 'block';
}

function closeRoomInfoModal() {
    document.getElementById('roomInfoOverlay').style.display = 'none';
    document.getElementById('roomInfoModal').style.display = 'none';
    
    // 停止据点弹窗粒子系统
    if (modalParticleSystem) {
        modalParticleSystem.stop();
    }
}

// 房间信息弹窗侧边栏控制函数
function toggleRoomInfoSidebar() {
    var sidebar = document.getElementById('roomInfoSidebar');
    var icon = document.getElementById('roomInfoSidebarIcon');
    
    if (sidebar.classList.contains('room-info-sidebar-collapsed')) {
        // 展开侧边栏
        sidebar.classList.remove('room-info-sidebar-collapsed');
        icon.textContent = '◀';
    } else {
        // 收起侧边栏
        sidebar.classList.add('room-info-sidebar-collapsed');
        icon.textContent = '▶';
    }
}

// 我的房间弹窗函数
function showMyOutpostsModal() {
    var outpostList = document.getElementById('myOutpostsList');
    outpostList.innerHTML = '';
    
    if (userRooms.length === 0) {
        outpostList.innerHTML = '<div style="color:#9ca3af;text-align:center;padding:20px">暂无房间，点击地图创建您的第一个房间</div>';
    } else {
        userRooms.forEach(function(room) {
            var outpostItem = document.createElement('div');
            outpostItem.className = 'outpost-item';
            outpostItem.onclick = function() {
                closeMyOutpostsModal();
                locateToOutpost(room);
            };
            
            outpostItem.innerHTML = 
                '<div class="outpost-item-name">🏰 ' + room.name + '</div>' +
                '<div class="outpost-item-details">房主：' + room.owner + '</div>';
            
            outpostList.appendChild(outpostItem);
        });
    }
    
    document.getElementById('myOutpostsOverlay').style.display = 'block';
    document.getElementById('myOutpostsModal').style.display = 'block';
}

function closeMyOutpostsModal() {
    document.getElementById('myOutpostsOverlay').style.display = 'none';
    document.getElementById('myOutpostsModal').style.display = 'none';
}

// 定位到指定房间所属的据点
function locateToOutpost(room) {
    if (room.fortress_id) {
        // 根据房间的fortress_id找到对应的据点
        var fortress = fortresses.find(function(f) {
            return f.id === room.fortress_id;
        });
        
        if (fortress && fortress.x && fortress.y) {
            // 计算据点在地图上的位置（据点坐标已经是像素坐标）
            var targetX = -fortress.x * scale + window.innerWidth / 2;
            var targetY = -fortress.y * scale + window.innerHeight / 2;
            
            // 应用边界限制
            var mapWidth = 4081 * scale;
            var mapHeight = 5488 * scale;
            var containerWidth = window.innerWidth;
            var containerHeight = window.innerHeight;
            
            var minX, minY, maxX, maxY;
            
            if (mapWidth <= containerWidth) {
                minX = (containerWidth - mapWidth) / 2;
                maxX = minX;
                targetX = minX;
            } else {
                minX = containerWidth - mapWidth;
                maxX = 0;
                targetX = Math.max(minX, Math.min(maxX, targetX));
            }
            
            if (mapHeight <= containerHeight) {
                minY = (containerHeight - mapHeight) / 2;
                maxY = minY;
                targetY = minY;
            } else {
                minY = containerHeight - mapHeight;
                maxY = 0;
                targetY = Math.max(minY, Math.min(maxY, targetY));
            }
            
            // 平滑移动到目标位置
            mapX = targetX;
            mapY = targetY;
            updateMapPosition();
        }
    }
}

// 高亮显示房间
function highlightOutpost(roomId) {
    var outposts = document.querySelectorAll('.outpost');
    outposts.forEach(function(outpost) {
        if (outpost.dataset.roomId == roomId) {
            outpost.style.boxShadow = '0 0 30px #2dd4bf, 0 0 60px #2dd4bf';
            setTimeout(function() {
                outpost.style.boxShadow = '';
            }, 2000);
        }
    });
}

// 侧边栏控制函数
function toggleSidebar() {
    var sidebar = document.getElementById('tacticalSidebar');
    var icon = document.getElementById('sidebarToggleIcon');
    
    if (sidebar.classList.contains('sidebar-collapsed')) {
        // 展开侧边栏
        sidebar.classList.remove('sidebar-collapsed');
        sidebar.classList.add('sidebar-expanded');
        icon.textContent = '✕';
        renderSidebarOutposts();
    } else {
        // 收起侧边栏
        sidebar.classList.remove('sidebar-expanded');
        sidebar.classList.add('sidebar-collapsed');
        icon.textContent = '⚔️';
    }
}

// 渲染侧边栏房间列表
function renderSidebarOutposts() {
    var outpostList = document.getElementById('sidebarOutpostList');
    outpostList.innerHTML = '';
    
    if (rooms.length === 0) {
        outpostList.innerHTML = '<div style="color:#9ca3af;text-align:center;padding:10px;font-size:11px">暂无房间</div>';
    } else {
        // 按在线人数排序
        var sortedRooms = rooms.slice().sort(function(a, b) {
            return (b.online_count || 0) - (a.online_count || 0);
        });
        
        sortedRooms.forEach(function(room) {
            var outpostItem = document.createElement('div');
            outpostItem.className = 'sidebar-outpost-item';
            outpostItem.onclick = function() {
                locateToOutpost(room);
            };
            
            var onlineCount = room.online_count || 0;
            var statusIcon = onlineCount >= 6 ? '🔥' : onlineCount >= 2 ? '⚡' : '💤';
            var statusColor = onlineCount >= 6 ? '#ef4444' : onlineCount >= 2 ? '#3b82f6' : '#2dd4bf';
            
            outpostItem.innerHTML = 
                '<div class="sidebar-outpost-name">' + statusIcon + ' ' + room.name + '</div>' +
                '<div class="sidebar-outpost-info">房主：' + room.owner + ' | 在线：' + onlineCount + '人</div>';
            
            outpostList.appendChild(outpostItem);
        });
    }
}

// 据点弹窗粒子系统 - 参照房间页面实现
var modalParticleSystem = null;

class ModalParticleSystem {
    constructor() {
        this.canvas = document.getElementById('modalParticleCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.mouseX = -1000;
        this.mouseY = -1000;
        this.config = {
            particleSize: 2,
            particleMargin: 2,
            repulsionRadius: 80,
            repulsionForce: 1.0,
            friction: 0.15,
            returnSpeed: 0.02,
            maxDisplayRatio: 0.8,
            samplingStep: 5,
            mobileRepulsionRadius: 60
        };
        this.isActive = false;
        this.modalRect = null;
    }
    
    init(imagePath) {
        if (!this.canvas) return;
        
        this.resizeCanvas();
        this.createPatternParticles(imagePath);
        this.isActive = true;
        this.animate();
        
        // 添加鼠标事件监听
        document.addEventListener('mousemove', (e) => {
            if (this.isActive) {
                this.updateMousePosition(e);
            }
        });
        
        window.addEventListener('resize', () => {
            this.resizeCanvas();
        });
    }
    
    updateMousePosition(e) {
        const modal = document.getElementById('roomInfoModal');
        if (modal && modal.style.display === 'block') {
            this.modalRect = modal.getBoundingClientRect();
            this.mouseX = e.clientX - this.modalRect.left;
            this.mouseY = e.clientY - this.modalRect.top;
        }
    }
    
    resizeCanvas() {
        const modal = document.getElementById('roomInfoModal');
        if (modal && modal.style.display === 'block') {
            this.canvas.width = modal.offsetWidth;
            this.canvas.height = modal.offsetHeight;
            this.modalRect = modal.getBoundingClientRect();
        }
    }
    
    createPatternParticles(imagePath) {
        this.particles = [];
        const canvasWidth = this.canvas.width;
        const canvasHeight = this.canvas.height;
        const maxDisplayWidth = canvasWidth * this.config.maxDisplayRatio;
        const maxDisplayHeight = canvasHeight * this.config.maxDisplayRatio;
        
        // 使用传入的图片路径加载图片并创建粒子
        this.loadImageAndCreateParticles(imagePath);
    }
    
    loadImageAndCreateParticles(imageSrc) {
        console.log('开始加载图片并创建粒子...');
        const img = new Image();
        img.src = imageSrc;
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
            console.log('创建备用图案粒子');
            this.createFallbackPattern();
        };
    }
    
    createParticlesFromImage(img) {
        const canvasWidth = this.canvas.width;
        const canvasHeight = this.canvas.height;
        const maxDisplayWidth = canvasWidth * this.config.maxDisplayRatio;
        const maxDisplayHeight = canvasHeight * this.config.maxDisplayRatio;
        
        const tempCanvas = document.createElement('canvas');
        const tempCtx = tempCanvas.getContext('2d');
        
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
                    const particle = new ModalParticle(
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
    
    createFallbackPattern() {
        const canvasWidth = this.canvas.width;
        const canvasHeight = this.canvas.height;
        const centerX = canvasWidth / 2;
        const centerY = canvasHeight / 2;
        const maxRadius = Math.min(centerX, centerY) * 0.9;
        
        // 创建多层圆形图案
        for (let layer = 0; layer < 5; layer++) {
            const layerRadius = maxRadius * (0.2 + layer * 0.15);
            const particleCount = 20 + layer * 10;
            
            for (let i = 0; i < particleCount; i++) {
                const angle = (i / particleCount) * Math.PI * 2;
                const radiusVariation = layerRadius * (0.8 + Math.random() * 0.4);
                const x = centerX + Math.cos(angle) * radiusVariation;
                const y = centerY + Math.sin(angle) * radiusVariation;
                const colorType = layer % 2 === 0 ? 'light' : 'dark';
                this.particles.push(new ModalParticle(x, y, this.config, colorType));
            }
        }
    }
    
    getPixelBrightness(imgData, x, y) {
        const i = (y * imgData.width + x) * 4;
        return (imgData.data[i] + imgData.data[i + 1] + imgData.data[i + 2]) / 3;
    }
    
    animate() {
        if (!this.isActive) return;
        
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        this.particles.forEach(particle => {
            particle.update(this.mouseX, this.mouseY, this.canvas.width, this.canvas.height);
            particle.draw(this.ctx);
        });
        
        requestAnimationFrame(() => this.animate());
    }
    
    start() {
        this.isActive = true;
        this.resizeCanvas();
        this.animate();
    }
    
    stop() {
        this.isActive = false;
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
}

class ModalParticle {
    constructor(x, y, config, colorType) {
        this.x = x;
        this.y = y;
        this.vx = (Math.random() - 0.5) * 0.5;
        this.vy = (Math.random() - 0.5) * 0.5;
        this.config = config;
        this.colorType = colorType;
        this.opacity = Math.random() * 0.5 + 0.3;
        this.originalX = x;
        this.originalY = y;
    }
    
    update(mouseX, mouseY, canvasWidth, canvasHeight) {
        // 鼠标排斥效果
        const dx = this.x - mouseX;
        const dy = this.y - mouseY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < this.config.repulsionRadius) {
            const force = (1 - distance / this.config.repulsionRadius) * this.config.repulsionForce;
            const angle = Math.atan2(dy, dx);
            this.vx += Math.cos(angle) * force;
            this.vy += Math.sin(angle) * force;
        }
        
        // 添加向原位置的恢复力
        this.vx += (this.originalX - this.x) * this.config.returnSpeed;
        this.vy += (this.originalY - this.y) * this.config.returnSpeed;
        
        // 应用摩擦力
        this.vx *= (1 - this.config.friction);
        this.vy *= (1 - this.config.friction);
        
        // 更新位置
        this.x += this.vx;
        this.y += this.vy;
        
        // 边界检测
        if (this.x < 0 || this.x > canvasWidth) {
            this.vx *= -0.8;
            this.x = Math.max(0, Math.min(canvasWidth, this.x));
        }
        if (this.y < 0 || this.y > canvasHeight) {
            this.vy *= -0.8;
            this.y = Math.max(0, Math.min(canvasHeight, this.y));
        }
    }
    
    draw(ctx) {
        const color = this.colorType === 'light' 
            ? `rgba(45, 212, 191, ${this.opacity})`
            : `rgba(139, 92, 246, ${this.opacity})`;
        
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.config.particleSize, 0, Math.PI * 2);
        ctx.fill();
    }
}

// 初始化
window.addEventListener('load', function() {
    centerMap();
    
    // 检查据点数据
    console.log('据点数量:', fortresses.length);
    if (fortresses.length > 0) {
        console.log('第一个据点:', fortresses[0]);
    }
    
    renderFortresses(); // 渲染据点系统
    
    // 初始化据点弹窗粒子系统
    modalParticleSystem = new ModalParticleSystem();
});

window.addEventListener('resize', centerMap);
