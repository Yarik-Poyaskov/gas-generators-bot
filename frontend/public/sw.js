self.addEventListener('push', function(event) {
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body,
      vibrate: [100, 50, 100],
      data: {
        dateOfArrival: Date.now(),
        primaryKey: '2'
      },
      actions: [
        {action: 'explore', title: 'Відкрити дашборд'},
        {action: 'close', title: 'Закрити'},
      ]
    };
    event.waitUntil(
      self.registration.showNotification(data.title, options)
    );
  }
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/')
    );
  } else {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// PWA Caching Logic
const CACHE_NAME = 'gpu-dashboard-pwa-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/login',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png'
];

// Install Service Worker and cache core shell assets
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

// Activate Service Worker and clean up old caches
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Intercept fetch requests for caching with Stale-While-Revalidate strategy
self.addEventListener('fetch', function(event) {
  const url = new URL(event.request.url);

  // Exclude WebSockets, API calls, and non-GET requests from caching
  if (
    url.protocol === 'ws:' || 
    url.protocol === 'wss:' || 
    url.pathname.includes('/api/') ||
    event.request.method !== 'GET'
  ) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then(function(cachedResponse) {
      // Fetch dynamic version in background to update cache
      const fetchPromise = fetch(event.request)
        .then(function(networkResponse) {
          if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then(function(cache) {
              cache.put(event.request, responseToCache);
            });
          }
          return networkResponse;
        })
        .catch(function() {
          // Silent catch for network failures during background sync
        });

      // If asset is cached, return it immediately, update in background
      if (cachedResponse) {
        return cachedResponse;
      }

      // If asset is not in cache, wait for network fetch
      return fetchPromise.then(function(res) {
        if (res) return res;
        return fetch(event.request);
      }).catch(function() {
        // Fallback for navigation requests when completely offline
        if (event.request.mode === 'navigate') {
          return caches.match('/');
        }
      });
    })
  );
});

