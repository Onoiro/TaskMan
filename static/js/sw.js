const CACHE_NAME = 'taskman-v2';

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll([
      '/',
      '/static/css/custom.css',
      '/static/icons/icon-192x192.png',
      '/static/icons/icon-180x180.png',
      '/static/icons/icon-512x512.png',
      '/static/images/favicon.ico'
    ]))
  );
});

// handler activate for remove old caches
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keyList) => {
      return Promise.all(keyList.map((key) => {
        if (key !== CACHE_NAME) {
          return caches.delete(key);
        }
      }));
    })
  );
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((response) => {
      return response || fetch(e.request);
    })
  );
});
