const CACHE_NAME = 'taskman-v10';

const CRITICAL_ASSETS = [
  '/static/css/custom.css',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-180x180.png',
  '/static/icons/icon-512x512.png',
  '/static/images/favicon.ico',
  '/static/offline.html'
];

const EXTERNAL = [
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js'
];

// Установка
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => Promise.all([
        cache.addAll(CRITICAL_ASSETS),
        cache.addAll(EXTERNAL)
      ]))
      .then(() => self.skipWaiting())
  );
});

// Активация
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

// Fetch
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;

  const url = new URL(e.request.url);

  // Все навигационные запросы (HTML-страницы): Network First
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then(response => {
          // Кешируем успешные ответы
          if (response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(e.request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          // Сначала пробуем кешированную версию страницы
          return caches.match(e.request)
            .then(cached => cached || caches.match('/static/offline.html'));
        })
    );
    return;
  }

  // Статические файлы: Cache First
  if (url.pathname.startsWith('/static/') ||
      url.hostname.includes('cdn.jsdelivr.net')) {
    e.respondWith(
      caches.match(e.request)
        .then(response => {
          if (response) return response;
          return fetch(e.request).then(fetchResponse => {
            if (fetchResponse.status === 200) {
              const clone = fetchResponse.clone();
              caches.open(CACHE_NAME).then(cache => {
                cache.put(e.request, clone);
              });
            }
            return fetchResponse;
          });
        })
        .catch(() => new Response('', { status: 408 }))
    );
    return;
  }

  // API/другие запросы: Network Only
  e.respondWith(fetch(e.request));
});
