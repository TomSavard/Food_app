// Service Worker for PWA.
// Strategy: network-first for HTML/navigation, cache-first for static assets.
// Bump CACHE_NAME whenever you change which assets are pre-cached.
const CACHE_NAME = 'food-app-v2';
const urlsToCache = [
    '/css/styles.css',
    '/css/chat.css',
    '/js/api.js',
    '/js/app.js',
    '/js/chat.js',
    '/js/shopping-list.js',
    '/js/ingredients.js',
    '/manifest.json',
];

self.addEventListener('install', (event) => {
    self.skipWaiting();
    event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(urlsToCache)));
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        Promise.all([
            caches.keys().then((names) =>
                Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)))
            ),
            self.clients.claim(),
        ])
    );
});

self.addEventListener('fetch', (event) => {
    const req = event.request;
    const accept = req.headers.get('accept') || '';
    const isHTML = req.mode === 'navigate' || accept.includes('text/html');

    if (isHTML) {
        // Network-first: always try the network; fall back to cache offline.
        event.respondWith(
            fetch(req).catch(() => caches.match(req).then((r) => r || caches.match('/')))
        );
        return;
    }

    // Cache-first for static assets.
    event.respondWith(caches.match(req).then((r) => r || fetch(req)));
});
