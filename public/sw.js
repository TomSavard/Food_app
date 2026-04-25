// Service Worker for PWA.
// Strategy: network-first for HTML/navigation, cache-first for static assets.
// Bump CACHE_NAME whenever you change the precache list.
const CACHE_NAME = 'food-app-v6';
const urlsToCache = [
    '/',
    '/meal-plan',
    '/shopping',
    '/ingredients',
    '/manifest.json',
    '/images/icon-192.png',
    '/images/icon-512.png',
];

self.addEventListener('install', (event) => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) =>
            // Best-effort precache; don't fail install if a URL is unavailable yet.
            Promise.all(urlsToCache.map((u) => cache.add(u).catch(() => null)))
        )
    );
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
    if (req.method !== 'GET') return;
    const accept = req.headers.get('accept') || '';
    const isHTML = req.mode === 'navigate' || accept.includes('text/html');

    if (isHTML) {
        event.respondWith(
            fetch(req).catch(() => caches.match(req).then((r) => r || caches.match('/')))
        );
        return;
    }

    event.respondWith(caches.match(req).then((r) => r || fetch(req)));
});
