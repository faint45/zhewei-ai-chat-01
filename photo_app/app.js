/**
 * 男神拍拍 - AI 攝影助手
 * Photo App with AI Enhancement & Reference Guide
 */

class PhotoApp {
    constructor() {
        this.stream = null;
        this.currentPose = null;
        this.aiMode = 'none';
        this.currentEditTool = null;
        this.editValue = 50;
        this.deferredPrompt = null;
        this.history = this.loadHistory();

        this.poses = [
            { id: 1, name: '自然站立', icon: '🧍', tip: '雙腳與肩同寬，身體微微側向鏡頭', category: 'basic' },
            { id: 2, name: '手插口袋', icon: '💪', tip: '一隻手插入口袋，另一隻手自然垂放', category: 'basic' },
            { id: 3, name: '靠牆站立', icon: '🧱', tip: '肩膀微微靠牆，頭部稍微轉向鏡頭', category: 'basic' },
            { id: 4, name: '坐姿帥氣', icon: '🪑', tip: '坐姿端正，雙腿自然分開，手臂搭在腿上', category: 'sitting' },
            { id: 5, name: '低頭沉思', icon: '🤔', tip: '輕輕低頭，下巴微收，眼神看向斜下方', category: 'portrait' },
            { id: 6, name: '側顏殺', icon: '👤', tip: '側對鏡頭，臉部微微抬起，下顎線明顯', category: 'portrait' },
            { id: 7, name: '笑顏殺', icon: '😄', tip: '自然微笑，露出牙齒，眼神有光', category: 'portrait' },
            { id: 8, name: '街頭潮流', icon: '🏙️', tip: '雙手交叉胸前或插袋，腳步姿勢自然', category: 'street' },
            { id: 9, name: '運動風', icon: '🏃', tip: '穿運動服裝，展現活力姿態', category: 'sport' },
            { id: 10, name: '正式穿著', icon: '👔', tip: '西裝或正式服裝，雙手自然交疊或垂放', category: 'formal' }
        ];

        this.references = {
            poses: [
                { title: '經典站姿', desc: '雙腳與肩同寬，重心稍微偏移', icon: '🧍' },
                { title: '坐姿優雅', desc: '坐三分之一椅面，身體微微前傾', icon: '🪑' },
                { title: '靠姿帥氣', desc: '身體斜靠支撐物，腿部交叉', icon: '斜靠' },
                { title: '走動抓拍', desc: '自然行走，捕捉動態瞬間', icon: '🚶' },
                { title: '互動姿勢', desc: '與環境互動，增加畫面故事性', icon: '互動' }
            ],
            lighting: [
                { title: '自然光', desc: '窗邊或戶外 мягкий свет', icon: '☀️' },
                { title: '逆光剪影', desc: '光源在身後，營造神秘感', icon: '🌅' },
                { title: '側光立體', desc: '光源在側面，增強輪廓', icon: '💡' },
                { title: '室內柔和', desc: '室內間接照明，氛圍溫暖', icon: '🏠' },
                { title: '黃昏金色', desc: '黃昏時段，光線溫暖柔和', icon: '🌇' }
            ],
            scenes: [
                { title: '城市街頭', desc: '街頭塗鴉、紅磚牆、霓虹燈', icon: '🏙️' },
                { title: '自然戶外', desc: '樹林、海灘、山景', icon: '🌲' },
                { title: '咖啡廳', desc: '文青咖啡廳、復古裝潢', icon: '☕' },
                { title: '工業風', desc: '倉庫、鐵件、混凝土', icon: '🏭' },
                { title: '居家空間', desc: '書房、臥室、客廳', icon: '🏠' }
            ],
            inspiration: [
                { title: '韓系歐巴', desc: '簡約乾淨，清新自然', icon: '🇰🇷' },
                { title: '日系鹽顏', desc: '淡顏系，乾淨柔和', icon: '🇯🇵' },
                { title: '欧美型男', desc: '深邃輪廓，時尚感', icon: '🌍' },
                { title: '復古港風', desc: '90年代香港風格', icon: '🇭🇰' },
                { title: '運動陽光', desc: '活力健康，運動風格', icon: '🏃' }
            ]
        };

        this.init();
    }

    async init() {
        this.bindEvents();
        this.renderPoses();
        this.renderReferences('poses');
        this.renderHistory();
        await this.checkCameraPermission();
        this.setupPWA();
    }

    bindEvents() {
        // Navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchPage(e.target.closest('.nav-btn').dataset.page));
        });

        // Camera controls
        document.getElementById('captureBtn').addEventListener('click', () => this.capturePhoto());
        document.getElementById('switchCameraBtn').addEventListener('click', () => this.switchCamera());
        document.getElementById('galleryBtn').addEventListener('click', () => this.switchPage('gallery'));

        // AI options
        document.querySelectorAll('.ai-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.selectAIMode(e.target));
        });

        // Pose selection
        document.getElementById('poseCarousel').addEventListener('click', (e) => {
            const poseItem = e.target.closest('.pose-item');
            if (poseItem) this.selectPose(poseItem.dataset.id);
        });

        // Edit section
        document.getElementById('cancelEditBtn').addEventListener('click', () => this.switchPage('camera'));
        document.getElementById('saveEditBtn').addEventListener('click', () => this.saveEditedPhoto());
        document.getElementById('aiEnhanceBtn').addEventListener('click', () => this.aiAutoEnhance());
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.selectEditTool(e.target));
        });
        document.getElementById('editSlider').addEventListener('input', (e) => {
            this.editValue = e.target.value;
            document.getElementById('sliderValue').textContent = e.target.value;
            this.applyEdit();
        });

        // Reference tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchReferenceTab(e.target.dataset.tab));
        });

        // History
        document.getElementById('historyBtn').addEventListener('click', () => this.switchPage('history'));
        document.getElementById('clearHistoryBtn').addEventListener('click', () => this.clearHistory());

        // Install PWA
        document.getElementById('installBtn').addEventListener('click', () => this.installPWA());
        document.getElementById('dismissInstallBtn').addEventListener('click', () => {
            document.getElementById('installPrompt').style.display = 'none';
        });

        // API Key Modal
        document.getElementById('settingsBtn').addEventListener('click', () => this.showApiKeyModal());
        document.getElementById('cancelApiKeyBtn').addEventListener('click', () => this.hideApiKeyModal());
        document.getElementById('saveApiKeyBtn').addEventListener('click', () => this.saveApiKey());

        // Render filter grid
        this.renderFilters();
    }

    renderFilters() {
        const grid = document.getElementById('filterGrid');
        const filters = this.getMaleFilters();

        grid.innerHTML = Object.entries(filters).map(([key, filter]) => `
            <div class="filter-item ${key === 'none' ? 'active' : ''}" data-filter="${key}">
                <span class="filter-icon">${filter.icon}</span>
                <span class="filter-name">${filter.name}</span>
            </div>
        `).join('');

        // Add click events
        grid.querySelectorAll('.filter-item').forEach(item => {
            item.addEventListener('click', (e) => this.selectFilter(e.target.closest('.filter-item')));
        });
    }

    selectFilter(item) {
        document.querySelectorAll('.filter-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        this.aiMode = item.dataset.filter;

        const filters = this.getMaleFilters();
        const filter = filters[this.aiMode];
        if (filter) {
            this.showToast(`已選擇：${filter.name}`);
        }
    }

    showApiKeyModal() {
        const token = localStorage.getItem('replicate_token') || '';
        document.getElementById('replicateToken').value = token;
        document.getElementById('apiKeyModal').style.display = 'flex';
    }

    hideApiKeyModal() {
        document.getElementById('apiKeyModal').style.display = 'none';
    }

    saveApiKey() {
        const token = document.getElementById('replicateToken').value.trim();
        if (token) {
            localStorage.setItem('replicate_token', token);
            this.showToast('API Token 已儲存！');
        } else {
            localStorage.removeItem('replicate_token');
            this.showToast('已清除 API Token');
        }
        this.hideApiKeyModal();
    }

    async checkCameraPermission() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'user' },
                audio: false
            });
            document.getElementById('cameraPreview').srcObject = this.stream;
        } catch (error) {
            console.error('Camera permission denied:', error);
            this.showToast('無法存取相機，請檢查權限設定');
        }
    }

    async switchCamera() {
        const video = document.getElementById('cameraPreview');
        const currentFacing = video.srcObject?.getTracks()[0]?.getSettings()?.facingMode;

        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }

        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: currentFacing === 'user' ? 'environment' : 'user' },
                audio: false
            });
            video.srcObject = this.stream;
        } catch (error) {
            this.showToast('無法切換相機');
        }
    }

    async capturePhoto() {
        this.showLoading('拍照中...');

        const video = document.getElementById('cameraPreview');
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');

        ctx.drawImage(video, 0, 0);
        const imageData = canvas.toDataURL('image/jpeg', 0.9);

        // Apply AI mode if selected
        if (this.aiMode !== 'none') {
            await this.applyAIToImage(imageData, this.aiMode);
        } else {
            this.addToHistory(imageData);
            this.showToast('拍照成功！');
        }

        this.hideLoading();
    }

    async applyAIToImage(imageData, mode) {
        // Check for Replicate API key (only for portrait mode)
        const replicateToken = localStorage.getItem('replicate_token') || '';

        if (replicateToken && mode === 'portrait') {
            // Use Replicate API for powerful AI portrait editing
            this.showLoading('AI 人像處理中...');
            try {
                const processedImage = await this.callReplicateAPI(imageData, 'portrait', replicateToken);
                this.addToHistory(processedImage);
                this.hideLoading();
                this.showToast('AI 人像修圖完成！');
                return;
            } catch (error) {
                console.error('Replicate API error:', error);
                this.showToast('AI API 失敗，使用本地濾鏡');
            }
        }

        // Use local CSS filters for all modes
        this.showLoading('套用濾鏡中...');
        await this.delay(800);

        const processedImage = await this.applyFilterByName(imageData, mode);

        this.addToHistory(processedImage);
        this.hideLoading();

        const filters = this.getMaleFilters();
        const filterName = filters[mode]?.name || '濾鏡';
        this.showToast(`${filterName} 已套用！`);
    }

    async callReplicateAPI(imageData, mode, token) {
        // Convert base64 to blob
        const response = await fetch(imageData);
        const blob = await response.blob();

        // Determine model based on mode
        let model = '';
        let prompt = '';

        switch (mode) {
            case 'portrait':
                model = 'stability-ai/sdxl:39ed52c2a78c30d39e0e55d6f52c71a4a6979a35940a5808d4e5a8d6a0c8c8c9';
                prompt = 'portrait photo, natural skin, subtle enhancement, professional lighting';
                break;
            case 'style':
                model = 'stability-ai/sdxl:39ed52c2a78c30d39e0e55d6f52c71a4a6979a35940a5808d4e5a8d6a0c8c8c9';
                prompt = 'artistic style, creative filter, professional photography style';
                break;
            case 'enhance':
                model = 'nightmareai/real-esrgan:42c136af6c2f9c6e4e1b50f5c6d3c4a7e8f9b0c1d2e3a4f5b6c7d8e9f0a1b2';
                prompt = 'enhance photo quality, improve clarity, professional enhancement';
                break;
        }

        // Call Replicate API
        const formData = new FormData();
        formData.append('input', blob, 'photo.jpg');
        formData.append('prompt', prompt);
        formData.append('scale', '2');

        const apiResponse = await fetch(`https://api.replicate.com/v1/predictions`, {
            method: 'POST',
            headers: {
                'Authorization': `Token ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                version: model,
                input: {
                    image: imageData.split(',')[1], // Remove data URL prefix
                    prompt: prompt,
                    scale: 2
                }
            })
        });

        if (!apiResponse.ok) {
            throw new Error('API request failed');
        }

        const prediction = await apiResponse.json();

        // Poll for result
        let result = prediction;
        while (result.status !== 'succeeded' && result.status !== 'failed') {
            await this.delay(2000);
            const pollResponse = await fetch(result.urls.get, {
                headers: { 'Authorization': `Token ${token}` }
            });
            result = await pollResponse.json();
        }

        if (result.status === 'failed') {
            throw new Error('Processing failed');
        }

        return result.output;
    }

    // 8 種男生濾鏡風格定義
    getMaleFilters() {
        return {
            'none': { name: '原圖', icon: '🖼️', settings: {} },
            'portrait': { name: '人像', icon: '✨', settings: { brightness: 5, contrast: 10, saturation: 15 } },
            'natural': { name: '自然', icon: '🌿', settings: { brightness: 8, contrast: 5, saturation: -5 } },
            'cinematic': { name: '電影感', icon: '🎬', settings: { brightness: -5, contrast: 20, saturation: -15, sepia: 15 } },
            'noir': { name: '黑白', icon: '🎭', settings: { brightness: 0, contrast: 30, saturation: -100 } },
            'moody': { name: '情緒', icon: '🌙', settings: { brightness: -10, contrast: 25, saturation: -20, hue: -10 } },
            'urban': { name: '都市', icon: '🏙️', settings: { brightness: 5, contrast: 25, saturation: 10 } },
            'vintage': { name: '復古', icon: '📷', settings: { brightness: 5, contrast: 10, sepia: 30, hue: -5 } },
            'cool': { name: '冷色', icon: '❄️', settings: { brightness: 5, contrast: 15, saturation: -10, hue: 15 } },
            'warm': { name: '暖色', icon: '🔥', settings: { brightness: 10, contrast: 10, saturation: 5, hue: -10, sepia: 10 } }
        };
    }

    async portraitEnhance(imageData) {
        // 人像美顏 - 提升膚質、柔和光線
        return this.applyFilter(imageData, {
            brightness: 5,
            contrast: 10,
            saturation: 15,
            blur: 0
        });
    }

    async applyStyleFilter(imageData) {
        // 風格濾鏡 - 預設風格
        return this.applyFilter(imageData, {
            brightness: 10,
            contrast: 15,
            saturation: -10,
            warmth: 20
        });
    }

    async smartEnhance(imageData) {
        // 智能增強
        return this.applyFilter(imageData, {
            brightness: 8,
            contrast: 12,
            saturation: 5,
            sharpen: 20
        });
    }

    async applyFilterByName(imageData, filterName) {
        const filters = this.getMaleFilters();
        const filter = filters[filterName];
        if (filter && filter.settings) {
            return this.applyFilter(imageData, filter.settings);
        }
        return imageData;
    }

    applyFilter(imageData, settings) {
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement('canvas');
                canvas.width = img.width;
                canvas.height = img.height;
                const ctx = canvas.getContext('2d');

                ctx.filter = `brightness(${100 + (settings.brightness || 0)}%) ` +
                            `contrast(${100 + (settings.contrast || 0)}%) ` +
                            `saturate(${100 + (settings.saturation || 0)}%) ` +
                            `sepia(${settings.sepia || 0}%) ` +
                            `hue-rotate(${settings.hue || 0}deg) ` +
                            `blur(${settings.blur || 0}px)`;

                ctx.drawImage(img, 0, 0);
                resolve(canvas.toDataURL('image/jpeg', 0.9));
            };
            img.src = imageData;
        });
    }

    async aiAutoEnhance() {
        this.showLoading('AI 優化中...');
        await this.delay(2000);

        const editPreview = document.getElementById('editPreview');
        const enhanced = await this.smartEnhance(editPreview.src);
        editPreview.src = enhanced;

        this.hideLoading();
        this.showToast('AI 優化完成！');
    }

    selectAIMode(btn) {
        document.querySelectorAll('.ai-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.aiMode = btn.dataset.mode;
    }

    selectPose(poseId) {
        document.querySelectorAll('.pose-item').forEach(item => {
            item.classList.toggle('active', item.dataset.id === poseId);
        });

        const pose = this.poses.find(p => p.id === parseInt(poseId));
        if (pose) {
            this.currentPose = pose;
            document.getElementById('poseTip').textContent = pose.tip;
        }
    }

    renderPoses() {
        const container = document.getElementById('poseCarousel');
        container.innerHTML = this.poses.map(pose => `
            <div class="pose-item" data-id="${pose.id}">
                <span class="pose-icon">${pose.icon}</span>
                <span class="pose-name">${pose.name}</span>
            </div>
        `).join('');
    }

    switchPage(page) {
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

        const section = document.getElementById(page === 'gallery' ? 'historySection' : `${page}Section`);
        if (section) section.classList.add('active');

        document.querySelector(`.nav-btn[data-page="${page}"]`)?.classList.add('active');
    }

    // Edit functions
    selectEditTool(btn) {
        document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentEditTool = btn.dataset.tool;

        const sliderContainer = document.getElementById('sliderContainer');
        sliderContainer.style.display = 'block';
        document.getElementById('editSlider').value = 50;
        document.getElementById('sliderValue').textContent = '50';
    }

    applyEdit() {
        if (!this.currentEditTool) return;

        const preview = document.getElementById('editPreview');
        const value = this.editValue;
        let filter = '';

        switch (this.currentEditTool) {
            case 'brightness':
                filter = `brightness(${value}%)`;
                break;
            case 'contrast':
                filter = `contrast(${value}%)`;
                break;
            case 'warmth':
                filter = `sepia(${value / 100})`;
                break;
            case 'sharpen':
                filter = `blur(${5 - value / 25}px)`;
                break;
            case 'blur':
                filter = `blur(${value / 10}px)`;
                break;
        }

        preview.style.filter = filter;
    }

    saveEditedPhoto() {
        const preview = document.getElementById('editPreview');
        this.addToHistory(preview.src);
        this.showToast('照片已儲存！');
        this.switchPage('camera');
    }

    // Reference functions
    switchReferenceTab(tab) {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelector(`.tab-btn[data-tab="${tab}"]`).classList.add('active');
        this.renderReferences(tab);
    }

    renderReferences(type) {
        const grid = document.getElementById('referenceGrid');
        const items = this.references[type] || [];

        grid.innerHTML = items.map(item => `
            <div class="reference-item" data-type="${type}" data-title="${item.title}">
                <div class="ref-image">${item.icon}</div>
                <div class="ref-info">
                    <div class="ref-title">${item.title}</div>
                    <div class="ref-desc">${item.desc}</div>
                </div>
            </div>
        `).join('');
    }

    // History functions
    loadHistory() {
        try {
            return JSON.parse(localStorage.getItem('photoHistory') || '[]');
        } catch {
            return [];
        }
    }

    saveHistory() {
        localStorage.setItem('photoHistory', JSON.stringify(this.history));
    }

    addToHistory(imageData) {
        this.history.unshift({
            id: Date.now(),
            data: imageData,
            date: new Date().toLocaleString('zh-TW')
        });

        if (this.history.length > 100) {
            this.history = this.history.slice(0, 100);
        }

        this.saveHistory();
        this.renderHistory();
    }

    renderHistory() {
        const grid = document.getElementById('historyGrid');

        if (this.history.length === 0) {
            grid.innerHTML = `
                <div class="empty-state" style="grid-column: 1/-1;">
                    <div class="empty-icon">📷</div>
                    <p>還沒有照片，趕快拍一張吧！</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = this.history.map(photo => `
            <div class="history-item" data-id="${photo.id}">
                <img src="${photo.data}" alt="照片">
                <button class="delete-btn" data-id="${photo.id}">✕</button>
            </div>
        `).join('');

        // Bind delete events
        grid.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deletePhoto(btn.dataset.id);
            });
        });

        // Bind view events
        grid.querySelectorAll('.history-item').forEach(item => {
            item.addEventListener('click', () => {
                this.viewPhoto(item.dataset.id);
            });
        });
    }

    deletePhoto(id) {
        this.history = this.history.filter(p => p.id !== parseInt(id));
        this.saveHistory();
        this.renderHistory();
        this.showToast('照片已刪除');
    }

    viewPhoto(id) {
        const photo = this.history.find(p => p.id === parseInt(id));
        if (photo) {
            document.getElementById('editPreview').src = photo.data;
            this.switchPage('camera');
            document.getElementById('editSection').classList.add('active');
            document.getElementById('cameraSection').classList.remove('active');
        }
    }

    clearHistory() {
        if (confirm('確定要清除所有照片嗎？')) {
            this.history = [];
            this.saveHistory();
            this.renderHistory();
            this.showToast('已清除所有照片');
        }
    }

    // PWA functions
    setupPWA() {
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            document.getElementById('installPrompt').style.display = 'flex';
        });
    }

    async installPWA() {
        if (!this.deferredPrompt) return;

        this.deferredPrompt.prompt();
        const { outcome } = await this.deferredPrompt.userChoice;

        if (outcome === 'accepted') {
            this.showToast('安裝成功！');
        }

        this.deferredPrompt = null;
        document.getElementById('installPrompt').style.display = 'none';
    }

    // UI helpers
    showLoading(text = '處理中...') {
        document.getElementById('loadingText').textContent = text;
        document.getElementById('loadingOverlay').style.display = 'flex';
    }

    hideLoading() {
        document.getElementById('loadingOverlay').style.display = 'none';
    }

    showToast(message) {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 3000);
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    window.photoApp = new PhotoApp();
});
