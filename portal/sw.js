// Service Worker for Portal PWA
const DEBUG = false;
const CACHE_VERSION = '2.2.0';
const CACHE_NAME = `zhewei-portal-v${CACHE_VERSION}`;
const RUNTIME_CACHE = 'zhewei-runtime';

// 需要快取的靜態資源
const STATIC_CACHE_URLS = [
  '/',
  '/manifest.json',
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// 安裝事件 - 快取靜態資源
self.addEventListener('install', (event) => {
  if (DEBUG) console.log('[SW] Installing Service Worker...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        if (DEBUG) console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_CACHE_URLS);
      })
      .then(() => self.skipWaiting())
      .catch(err => console.error('[SW] Install failed:', err))
  );
});

// 啟用事件 - 清理舊快取
self.addEventListener('activate', (event) => {
  if (DEBUG) console.log('[SW] Activating Service Worker...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && cacheName !== RUNTIME_CACHE) {
            if (DEBUG) console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
      .catch(err => console.error('[SW] Activate failed:', err))
  );
});

// Fetch 事件 - 網路優先策略 (Network First)
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // 跳過非 HTTP(S) 請求
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // HTML 頁面請求 - 網路優先（確保登入閘門更新）
  if (request.destination === 'document' || url.pathname === '/') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const responseClone = response.clone();
            caches.open(RUNTIME_CACHE).then((cache) => {
              cache.put(request, responseClone);
            }).catch(() => {});
          }
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // API 請求 - 網路優先
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // 快取成功的 API 回應
          if (response.ok) {
            const responseClone = response.clone();
            caches.open(RUNTIME_CACHE).then((cache) => {
              cache.put(request, responseClone);
            }).catch(() => {});
          }
          return response;
        })
        .catch(() => {
          // 網路失敗時使用快取
          return caches.match(request);
        })
    );
    return;
  }

  // 靜態資源 - 快取優先
  event.respondWith(
    caches.match(request)
      .then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }

        return fetch(request).then((response) => {
          // 只快取成功的 GET 請求
          if (request.method === 'GET' && response.ok) {
            const responseClone = response.clone();
            caches.open(RUNTIME_CACHE).then((cache) => {
              cache.put(request, responseClone);
            }).catch(() => {});
          }
          return response;
        });
      })
      .catch(() => {
        // 離線時顯示離線頁面
        if (request.destination === 'document') {
          return new Response(
            `
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="UTF-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              <title>離線模式 - 築未科技</title>
              <style>
                body {
                  font-family: system-ui, -apple-system, sans-serif;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  min-height: 100vh;
                  margin: 0;
                  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                  color: white;
                  text-align: center;
                  padding: 20px;
                }
                .container {
                  max-width: 500px;
                }
                h1 { font-size: 3em; margin: 0 0 20px; }
                p { font-size: 1.2em; opacity: 0.9; }
                button {
                  margin-top: 30px;
                  padding: 15px 40px;
                  font-size: 1.1em;
                  background: white;
                  color: #667eea;
                  border: none;
                  border-radius: 8px;
                  cursor: pointer;
                  font-weight: bold;
                }
                button:hover { transform: scale(1.05); }
              </style>
            </head>
            <body>
              <div class="container">
                <h1>📡</h1>
                <h2>目前離線</h2>
                <p>無法連接到網路，請檢查您的網路連線。</p>
                <button onclick="location.reload()">重新連線</button>
              </div>
            </body>
            </html>
            `,
            {
              headers: { 'Content-Type': 'text/html' }
            }
          );
        }
      })
  );
});

// 推播通知
self.addEventListener('push', (event) => {
  if (DEBUG) console.log('[SW] Push received:', event);
  
  const data = event.data ? event.data.json() : {};
  const title = data.title || '築未科技通知';
  const options = {
    body: data.body || '您有新的通知',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/badge-72x72.png',
    vibrate: [200, 100, 200],
    data: data.url || '/',
    actions: [
      { action: 'open', title: '開啟' },
      { action: 'close', title: '關閉' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// 通知點擊
self.addEventListener('notificationclick', (event) => {
  if (DEBUG) console.log('[SW] Notification clicked:', event);
  event.notification.close();

  if (event.action === 'open' || !event.action) {
    const urlToOpen = event.notification.data || '/';
    event.waitUntil(
      clients.openWindow(urlToOpen)
    );
  }
});

// 背景同步
self.addEventListener('sync', (event) => {
  if (DEBUG) console.log('[SW] Background sync:', event.tag);
  
  if (event.tag === 'sync-data') {
    event.waitUntil(
      // 執行背景同步任務
      fetch('/api/sync')
        .then(response => response.json())
        .then(data => { if (DEBUG) console.log('[SW] Sync completed:', data); })
        .catch(err => console.error('[SW] Sync failed:', err))
    );
  }
});

// 訊息處理
self.addEventListener('message', (event) => {
  if (DEBUG) console.log('[SW] Message received:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CACHE_URLS') {
    event.waitUntil(
      caches.open(RUNTIME_CACHE)
        .then(cache => cache.addAll(event.data.urls))
        .catch(err => console.error('[SW] Cache URLs failed:', err))
    );
  }
  
  if (event.data && event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({
      version: CACHE_VERSION,
      cacheName: CACHE_NAME
    });
  }
  
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => caches.delete(cacheName))
        );
      }).then(() => {
        event.ports[0].postMessage({ success: true });
      }).catch(err => {
        console.error('[SW] Clear cache failed:', err);
        event.ports[0].postMessage({ success: false, error: err.message });
      })
    );
  }
});
