const CACHE_NAME = 'taskman-v1';
  self.addEventListener('install', (e) => {
    e.waitUntil(
      caches.open(CACHE_NAME).then((cache) => cache.addAll([
        '/',
        '/static/css/custom.css',
        '/static/icons/icon-192x192.png',
        '/static/icons/icon-180x180.png',
        '/static/images/favicon.ico'
      ]))
    );
  });
    