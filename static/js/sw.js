const CACHE_NAME = 'taskman-v1';
  self.addEventListener('install', (e) => {
    e.waitUntil(
      caches.open(CACHE_NAME).then((cache) => cache.addAll([
        '/',
        '/static/css/custom.css',
        '/static/js/app.js'
      ]))
    );
  });