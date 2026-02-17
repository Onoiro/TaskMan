// ВАЖНО: менять версию при КАЖДОМ деплое!
const CACHE_NAME = 'taskman-v11';

const CRITICAL_ASSETS = [
  '/static/css/vendor/bootstrap.min.css',
  '/static/css/vendor/bootstrap-icons.min.css',
  '/static/js/bootstrap.bundle.min.js',
  '/static/css/vendor/fonts/bootstrap-icons.woff2',
  '/static/css/custom.css',
  '/static/icons/emodji.png',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-180x180.png',
  '/static/icons/icon-512x512.png',
  '/static/images/favicon.ico',
  '/static/offline.html'
];

// Больше никаких EXTERNAL — всё локально!

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(CRITICAL_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then(keyList =>
        Promise.all(keyList.map(key => {
          if (key !== CACHE_NAME) return caches.delete(key);
        }))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;

  const url = new URL(e.request.url);

  // Навигация: Network First
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then(response => {
          if (response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
          }
          return response;
        })
        .catch(() =>
          caches.match(e.request)
            .then(cached => cached || caches.match('/static/offline.html'))
        )
    );
    return;
  }

  // Статика: Cache First
  if (url.pathname.startsWith('/static/')) {
    e.respondWith(
      caches.match(e.request)
        .then(response => {
          if (response) return response;
          return fetch(e.request).then(fetchResponse => {
            if (fetchResponse.status === 200) {
              const clone = fetchResponse.clone();
              caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
            }
            return fetchResponse;
          });
        })
        .catch(() => new Response('', { status: 408 }))
    );
    return;
  }

  // Остальное: Network Only
  e.respondWith(fetch(e.request));
});
