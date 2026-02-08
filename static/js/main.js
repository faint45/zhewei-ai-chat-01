// 主JavaScript文件 - 築未科技網站功能

document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有功能
    initNavbar();
    initScrollEffects();
    initContactForm();
    initAnimations();
    initServiceCards();
});

// 導航欄功能
function initNavbar() {
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    const navLinks = document.querySelectorAll('.nav-link');
    
    // 移動端菜單切換
    if (navToggle) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
            navToggle.classList.toggle('active');
        });
    }
    
    // 點擊導航鏈接關閉菜單
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            navMenu.classList.remove('active');
            navToggle.classList.remove('active');
        });
    });
    
    // 滾動時導航欄樣式變化
    window.addEventListener('scroll', function() {
        const navbar = document.querySelector('.navbar');
        if (window.scrollY > 100) {
            navbar.style.background = 'rgba(255, 255, 255, 0.98)';
            navbar.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.1)';
        } else {
            navbar.style.background = 'rgba(255, 255, 255, 0.95)';
            navbar.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
        }
    });
}

// 滾動效果
function initScrollEffects() {
    // 滾動到指定區域時觸發動畫
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);
    
    // 觀察所有需要動畫的元素
    const animateElements = document.querySelectorAll('.service-card, .product-card, .feature, .stat-item');
    animateElements.forEach(el => observer.observe(el));
    
    // 平滑滾動到指定區域
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                const offsetTop = targetElement.offsetTop - 80;
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// 聯繫表單功能
function initContactForm() {
    const contactForm = document.getElementById('contactForm');
    
    if (contactForm) {
        contactForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // 獲取表單數據
            const formData = new FormData(contactForm);
            const data = {
                name: contactForm.querySelector('input[type="text"]').value,
                email: contactForm.querySelector('input[type="email"]').value,
                phone: contactForm.querySelector('input[type="tel"]').value,
                message: contactForm.querySelector('textarea').value
            };
            
            // 表單驗證
            if (!validateForm(data)) {
                return;
            }
            
            // 顯示加載狀態
            const submitBtn = contactForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = '發送中...';
            submitBtn.disabled = true;
            
            // 模擬發送（實際開發中應替換為真實API調用）
            setTimeout(() => {
                // 顯示成功消息
                showNotification('感謝您的諮詢！我們將盡快與您聯繫。', 'success');
                
                // 重置表單
                contactForm.reset();
                
                // 恢復按鈕狀態
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
                
                // 記錄到控制台（開發用）
                console.log('表單提交數據:', data);
                
            }, 1500);
        });
    }
}

// 表單驗證
function validateForm(data) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const phoneRegex = /^[0-9\-\+\s\(\)]{10,}$/;
    
    if (!data.name.trim()) {
        showNotification('請輸入您的姓名', 'error');
        return false;
    }
    
    if (!emailRegex.test(data.email)) {
        showNotification('請輸入有效的電子郵件地址', 'error');
        return false;
    }
    
    if (data.phone && !phoneRegex.test(data.phone)) {
        showNotification('請輸入有效的電話號碼', 'error');
        return false;
    }
    
    if (!data.message.trim()) {
        showNotification('請輸入您的需求信息', 'error');
        return false;
    }
    
    return true;
}

// 顯示通知
function showNotification(message, type = 'info') {
    // 創建通知元素
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">&times;</button>
    `;
    
    // 添加樣式
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 10px;
        max-width: 300px;
        animation: slideInRight 0.3s ease-out;
    `;
    
    // 添加到頁面
    document.body.appendChild(notification);
    
    // 自動移除
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => notification.remove(), 300);
        }
    }, 5000);
}

// 動畫效果
function initAnimations() {
    // 添加動畫CSS
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOutRight {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        
        .animate-in {
            animation: fadeInUp 0.6s ease-out;
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .service-card:hover,
        .product-card:hover {
            transform: translateY(-5px) scale(1.02);
            transition: all 0.3s ease;
        }
    `;
    document.head.appendChild(style);
}

// 服務卡片交互
function initServiceCards() {
    const serviceCards = document.querySelectorAll('.service-card');
    
    serviceCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
        
        // 點擊卡片展開詳細信息
        card.addEventListener('click', function() {
            const details = this.querySelector('.service-details');
            if (details) {
                details.classList.toggle('expanded');
            }
        });
    });
}

// 頁面加載進度指示器
function initLoadingIndicator() {
    // 創建加載指示器
    const loader = document.createElement('div');
    loader.id = 'page-loader';
    loader.innerHTML = `
        <div class="loader-spinner" style="
            width: 50px;
            height: 50px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 15px;
        "></div>
        <p>加載中...</p>
    `;
    
    // 添加旋轉動畫
    const style = document.createElement('style');
    style.textContent = `
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);
    
    loader.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: white;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        z-index: 9999;
        transition: opacity 0.3s ease;
    `;
    
    document.body.appendChild(loader);
    
    // 隱藏加載層的函數
    function hideLoader() {
        loader.style.opacity = '0';
        setTimeout(() => {
            if (loader.parentElement) {
                loader.remove();
            }
        }, 300);
    }
    
    // 頁面加載完成後隱藏
    window.addEventListener('load', function() {
        setTimeout(hideLoader, 500);
    });
    
    // 超時機制：最多顯示 3 秒
    setTimeout(hideLoader, 3000);
}

// 性能優化：懶加載圖片
function initLazyLoading() {
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }
}

// 實時時鐘
function initRealTimeClock() {
    function updateClock() {
        const now = new Date();
        const timeString = now.toLocaleString('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
        
        const clockElement = document.getElementById('real-time-clock');
        if (clockElement) {
            clockElement.textContent = `當前時間: ${timeString}`;
        }
    }
    
    // 創建時鐘元素（如果需要的話）
    if (!document.getElementById('real-time-clock')) {
        const clock = document.createElement('div');
        clock.id = 'real-time-clock';
        clock.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 1000;
        `;
        document.body.appendChild(clock);
    }
    
    updateClock();
    setInterval(updateClock, 1000);
}

// 初始化所有功能
window.addEventListener('load', function() {
    initLoadingIndicator();
    initLazyLoading();
    initRealTimeClock();
});

// 導出函數供全局使用
window.showNotification = showNotification;
window.validateForm = validateForm;