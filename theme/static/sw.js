const CACHE_NAME = 'dossier-pwa-v1';
const URLS_TO_CACHE = [
    '/offline/',
    '/static/manifest.json',
    '/static/dossier_icon.png',
    '/static/css/dist/styles.css'
];

// Install: Cache core assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[Service Worker] Caching offline assets');
                return cache.addAll(URLS_TO_CACHE);
            })
    );
    self.skipWaiting();
});

// Activate: Cleanup old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('[Service Worker] Removing old cache', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// Fetch: Network first, fallback to cache, then offline page
self.addEventListener('fetch', (event) => {
    // Skip cross-origin requests or non-GET
    if (event.request.method !== 'GET') return;

    event.respondWith(
        fetch(event.request)
            .catch(() => {
                // Network failed
                return caches.match(event.request)
                    .then((cachedResponse) => {
                        if (cachedResponse) {
                            return cachedResponse;
                        }
                        // If navigation (HTML page), return offline page
                        if (event.request.mode === 'navigate') {
                            return caches.match('/offline/');
                        }
                    });
            })
    );
});
