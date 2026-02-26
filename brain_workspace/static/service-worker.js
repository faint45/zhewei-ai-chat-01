const CACHE_NAME = 'transfer-pwa-v1';
const urlsToCache = [
    '/transfer-receive.html',
    '/transfer-manifest.json'
];

self.addEventListener('install', (e) => {
    e.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache)));
});

self.addEventListener('fetch', (e) => {
    e.respondWith(caches.match(e.request).then(response => response || fetch(e.request)));
});

self.addEventListener('push', (e) => {
    const data = e.data?.json() || {};
    self.registration.showNotification(data.title || '新檔案', {
        body: data.body || '收到新檔案，請打開 App 查看',
        icon: '/static/icons/icon-192.png',
        tag: 'transfer'
    });
});
