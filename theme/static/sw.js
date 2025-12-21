// Minimal Service Worker (PWA)
self.addEventListener('install', (e) => {
    console.log('[Service Worker] Install');
    self.skipWaiting();
});

self.addEventListener('activate', (e) => {
    console.log('[Service Worker] Activate');
    e.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (e) => {
    // Pass through - no caching strategies implemented yet
});
