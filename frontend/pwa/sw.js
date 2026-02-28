// Service Worker for 築未科技 PWA (Cloudflare Pages 版)
const CACHE_VERSION = '3.1.0';
const CACHE_NAME = `zhewei-pwa-v${CACHE_VERSION}`;
const RUNTIME_CACHE = 'zhewei-pwa-runtime';

const STATIC_CACHE_URLS = [
  '/pwa/',
  '/pwa/manifest.json',
  '/pwa/icon-192.png',
  '/pwa/icon-512.png',
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css'
];

// 安裝
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_CACHE_URLS))
      .then(() => self.skipWaiting())
      .catch(err => console.error('[SW] Install failed:', err))
  );
});

// 啟用 — 清理舊快取
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(names =>
      Promise.all(names.map(n => (n !== CACHE_NAME && n !== RUNTIME_CACHE) ? caches.delete(n) : undefined))
    ).then(() => self.clients.claim())
  );
});

// Fetch — 網路優先
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (!url.protocol.startsWith('http')) return;

  // API 請求（跨域到 jarvis.zhe-wei.net）— 純網路
  if (url.hostname.includes('jarvis.zhe-wei.net') || url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(request).catch(() => caches.match(request)));
    return;
  }

  // Ntfy SSE — 不快取
  if (url.hostname.includes('notify.zhe-wei.net')) return;

  // HTML — 網路優先 + 快取 fallback
  if (request.destination === 'document') {
    event.respondWith(
      fetch(request).then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(RUNTIME_CACHE).then(c => c.put(request, clone)).catch(() => {});
        }
        return resp;
      }).catch(() => caches.match(request).then(r => r || offlinePage()))
    );
    return;
  }

  // 靜態資源 — 快取優先
  event.respondWith(
    caches.match(request).then(cached => {
      if (cached) return cached;
      return fetch(request).then(resp => {
        if (request.method === 'GET' && resp.ok) {
          const clone = resp.clone();
          caches.open(RUNTIME_CACHE).then(c => c.put(request, clone)).catch(() => {});
        }
        return resp;
      });
    }).catch(() => {
      if (request.destination === 'document') return offlinePage();
    })
  );
});

// 離線頁面
function offlinePage() {
  return new Response(`<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>離線 - 築未科技</title><style>body{font-family:system-ui;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:linear-gradient(135deg,#0a0f1e,#0c1929);color:white;text-align:center;padding:20px}h1{font-size:3em;margin:0 0 20px}button{margin-top:30px;padding:15px 40px;font-size:1.1em;background:white;color:#0ea5e9;border:none;border-radius:8px;cursor:pointer;font-weight:bold}</style></head><body><div><h1>📡</h1><h2>目前離線</h2><p>無法連接到網路，請檢查您的網路連線。</p><button onclick="location.reload()">重新連線</button></div></body></html>`, { headers: { 'Content-Type': 'text/html' } });
}

// ==================== Ntfy 推播通知 ====================
// Push 事件（來自 Ntfy 或 Web Push）
self.addEventListener('push', (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch(e) {
    try { data = { body: event.data.text() }; } catch(e2) {}
  }

  const title = data.title || '築未科技通知';
  const options = {
    body: data.body || data.message || '您有新的通知',
    icon: '/pwa/icon-192.png',
    badge: '/pwa/icon-192.png',
    vibrate: [200, 100, 200],
    data: { url: data.url || data.click || '/pwa/' },
    tag: data.tag || 'zhewei-' + Date.now(),
    actions: [
      { action: 'open', title: '開啟' },
      { action: 'close', title: '關閉' }
    ]
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

// 通知點擊
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'close') return;

  const url = (event.notification.data && event.notification.data.url) || '/pwa/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const client of list) {
        if (client.url.includes('/pwa') && 'focus' in client) return client.focus();
      }
      return clients.openWindow(url);
    })
  );
});

// 訊息處理
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting();
  if (event.data && event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: CACHE_VERSION, cacheName: CACHE_NAME });
  }
  // Ntfy 訊息轉推播
  if (event.data && event.data.type === 'NTFY_MESSAGE') {
    const d = event.data.payload || {};
    self.registration.showNotification(d.title || '築未科技', {
      body: d.message || d.body || '',
      icon: '/pwa/icon-192.png',
      badge: '/pwa/icon-192.png',
      vibrate: [200, 100, 200],
      data: { url: d.click || '/pwa/' },
      tag: 'ntfy-' + Date.now()
    });
  }
});
