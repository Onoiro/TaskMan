const CACHE_NAME = 'taskman-v9';

// Кешируем только критичные ресурсы
const CRITICAL_ASSETS = [
  '/static/css/custom.css',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-180x180.png', 
  '/static/icons/icon-512x512.png',
  '/static/images/favicon.ico'
];

const EXTERNAL = [
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js'
];

// Установка: кешируем критические ресурсы
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => Promise.all([
        cache.addAll(CRITICAL_ASSETS),
        cache.addAll(EXTERNAL)
      ]))
  );
});

// Активация: удаляем старые кеши
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then(keyList => 
      Promise.all(keyList.map(key => {
        if (key !== CACHE_NAME) return caches.delete(key);
      }))
    )
  );
});

// Fetch: стратегия Network First + Cache Fallback + ОФЛАЙН
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  
  // Игнорируем небезопасные запросы
  if (e.request.method !== 'GET') return;
  
  // Офлайн-страница для главной
  if (url.pathname === '/' && e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request).catch(() => 
        caches.match('/static/offline.html')
      ).catch(() => 
        new Response('TaskMan временно недоступен. Проверьте соединение.', {
          status: 503,
          statusText: 'Service Unavailable'
        })
      )
    );
    return;
  }
  
  // Статические файлы: Cache First
  if (url.pathname.startsWith('/static/') || url.hostname.includes('cdn.jsdelivr.net')) {
    e.respondWith(
      caches.match(e.request)
        .then(response => response || fetch(e.request))
        .catch(() => caches.match('/static/offline.html'))
    );
  }
});
