// =============================================================================
// Service Worker - Immo Luxembourg Dashboard PWA
// Version: 20260305-1910
// =============================================================================

const CACHE_NAME = 'immo-lux-v20260305-1910';
const STATIC_CACHE = 'immo-static-v1';
const DYNAMIC_CACHE = 'immo-dynamic-v1';

// Assets statiques à pré-cacher
const STATIC_ASSETS = [
  './',
  './index.html',
  './photos.html',
  './map.html',
  './new-listings.html',
  './stats-by-city.html',
  './alerts.html',
  './trends.html',
  './nearby.html',
  './icon.svg',
  './manifest.json',
  './dark-mode.js',
  './styles.css',
  './data/listings.js',
  './data/stats.js'
];

// CDN à cacher (stratégie network-first)
const CDN_HOSTS = [
  'cdn.jsdelivr.net',
  'unpkg.com',
  'fonts.googleapis.com',
  'fonts.gstatic.com'
];

// Installation - pré-cache des assets statiques
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('[SW] Pre-caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
      .catch(err => console.log('[SW] Pre-cache failed:', err))
  );
});

// Activation - nettoyage des anciens caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key =>
          key !== STATIC_CACHE &&
          key !== DYNAMIC_CACHE &&
          key !== CACHE_NAME
        ).map(key => {
          console.log('[SW] Deleting old cache:', key);
          return caches.delete(key);
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch - stratégies de cache
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignorer les requêtes non-GET
  if (request.method !== 'GET') return;

  // Stratégie pour CDN: network-first avec fallback cache
  if (CDN_HOSTS.some(host => url.hostname.includes(host))) {
    event.respondWith(networkFirst(request, DYNAMIC_CACHE));
    return;
  }

  // Stratégie pour données JSON: network-first (toujours à jour)
  if (url.pathname.includes('/data/') || url.pathname.endsWith('.json')) {
    event.respondWith(networkFirst(request, DYNAMIC_CACHE));
    return;
  }

  // Stratégie pour pages HTML: stale-while-revalidate
  if (request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(staleWhileRevalidate(request, STATIC_CACHE));
    return;
  }

  // Défaut: cache-first pour assets statiques
  event.respondWith(cacheFirst(request, STATIC_CACHE));
});

// === Stratégies de cache ===

// Cache first: rapide, utilise cache si disponible
async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    return new Response('Offline', { status: 503 });
  }
}

// Network first: données fraîches, fallback cache
async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await caches.match(request);
    return cached || new Response('Offline', { status: 503 });
  }
}

// Stale while revalidate: rapide + mise à jour en arrière-plan
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  const fetchPromise = fetch(request).then(response => {
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(() => cached);

  return cached || fetchPromise;
}

// Message handler pour refresh manuel
self.addEventListener('message', event => {
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
  }
});
