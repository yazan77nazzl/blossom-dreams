/* =========================================================================
   Blossom Dreams – Service Worker (PWA offline strategy)
   -------------------------------------------------------------------------
   - Cache-first (stale-while-revalidate) for static assets & CDN fonts.
   - Network-first (cache fallback) for the app shell / navigation and for
     public GET API endpoints (settings, services, categories, offers,
     gallery, availability) so bookings can still be explored offline.
   - NEVER intercepted: non-GET requests, and any API call NOT in the
     public allowlist (auth, bookings create/verify, admin endpoints, …).
   ========================================================================= */

const VERSION = 'blossom-dreams-v1';
const CORE_CACHE = `${VERSION}-core`;
const STATIC_CACHE = `${VERSION}-static`;
const API_CACHE = `${VERSION}-api`;

/* Keep the ?v= on these in sync with index.html asset versions. */
const ASSET_VERSION = '6.0';

const CORE_ASSETS = [
  '/',
  '/manifest.json',
  `/static/css/style.css?v=${ASSET_VERSION}`,
  `/static/js/app.js?v=${ASSET_VERSION}`,
  '/static/js/booking.js',
  '/static/js/api.js',
  '/static/images/hero_bg.jpg',
  '/static/images/icons/icon-192.png',
  '/static/images/icons/icon-512.png',
  '/static/images/icons/icon-maskable-512.png',
  '/static/images/icons/apple-touch-icon.png',
  'https://cdn.tailwindcss.com',
  'https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,600&family=Playfair+Display:ital,wght@0,500;0,600;0,700;0,800;1,400;1,600&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap'
];

/* Public, cacheable GET endpoints only. Everything else passes through. */
const PUBLIC_API = /^\/api\/(settings|services|categories|offers|gallery|availability)(\/|$)/;

const isStatic = (url) =>
  url.origin === self.location.origin ? url.pathname.startsWith('/static/') : true;

const isFont = (url) =>
  url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com';

const isCdn = (url) =>
  url.hostname === 'cdn.tailwindcss.com';

/* ------------------------------------------------------------------ install */
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) =>
        Promise.allSettled(CORE_ASSETS.map((asset) => cache.add(asset)))
      )
      .then(() => self.skipWaiting())
  );
});

/* ---------------------------------------------------------------- activate */
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => !key.startsWith(`${VERSION}-`))
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

/* ---------------------------------------------------------- page messaging */
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

/* -------------------------------------------------------------- utilities */
async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const fresh = await fetch(request);
    if (fresh && fresh.ok) {
      cache.put(request, fresh.clone());
    }
    return fresh;
  } catch (error) {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw error;
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cached = await cache.match(request);
  const background = () =>
    fetch(request)
      .then((response) => {
        if (response && (response.ok || response.type === 'opaque')) {
          cache.put(request, response.clone());
        }
      })
      .catch(() => undefined);
  if (cached) {
    background();
    return cached;
  }
  const network = await fetch(request);
  if (network && (network.ok || network.type === 'opaque')) {
    cache.put(request, network.clone());
  }
  return network;
}

async function navigationHandler(request) {
  const cache = await caches.open(CORE_CACHE);
  try {
    const fresh = await fetch(request);
    if (fresh && fresh.ok) {
      cache.put(request, fresh.clone());
    }
    return fresh;
  } catch (error) {
    const hit = await cache.match(request);
    if (hit) return hit;
    const home = await cache.match('/');
    if (home) return home;
    throw error;
  }
}

/* ------------------------------------------------------------------ fetch */
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== 'GET') {
    return; /* POST / PATCH / DELETE … always hit the network. */
  }

  /* Same-origin API calls. */
  if (url.origin === self.location.origin && url.pathname.startsWith('/api/')) {
    if (PUBLIC_API.test(url.pathname)) {
      event.respondWith(networkFirst(request, API_CACHE));
    }
    return; /* everything else: auth, bookings create/verify, admin → network. */
  }

  /* App shell / navigation (/, /admin, …). */
  if (request.mode === 'navigate' || request.destination === 'document') {
    event.respondWith(navigationHandler(request));
    return;
  }

  /* Static assets + Google Fonts + Tailwind CDN. */
  if (isStatic(url) || isFont(url) || isCdn(url)) {
    event.respondWith(staleWhileRevalidate(request));
  }

  /* Everything else (e.g. Instagram images) is left untouched. */
});