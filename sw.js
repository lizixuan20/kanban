/* 我的看板 · Service Worker */
const CACHE = 'kanban-v1';
const ASSETS = ['./', './index.html', './manifest.json',
                './vendor/echarts.min.js', './icons/icon-192.png', './icons/icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks =>
    Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  // 报价接口一律走网络，不缓存
  if (url.hostname.endsWith('gtimg.cn') || url.hostname.endsWith('sinajs.cn')) return;
  if (e.request.method !== 'GET') return;

  // 数据文件：先网络，失败用缓存
  if (url.pathname.endsWith('data.js')) {
    e.respondWith(
      fetch(e.request).then(r => {
        const copy = r.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
        return r;
      }).catch(() => caches.match(e.request))
    );
    return;
  }

  // 静态资源：先缓存，没有再网络
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(r => {
    const copy = r.clone();
    caches.open(CACHE).then(c => c.put(e.request, copy));
    return r;
  })));
});
