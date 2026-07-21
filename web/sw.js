/* Service Worker: legt die App-Hülle in den Cache, damit die Seite als
   installierte App startet. Kartenkacheln und API-Daten kommen weiter live
   aus dem Netz. */
const CACHE = "schnee-v1";
const ASSETS = [
  "./", "./index.html", "./manifest.webmanifest",
  "./icon-180.png", "./icon-512.png"
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;   // Kacheln, API, Suche: immer live

  // Seite selbst (Navigation): erst Netz, bei Offline aus dem Cache.
  // So kommen neue Versionen sofort durch, offline funktioniert es trotzdem.
  if (e.request.mode === "navigate") {
    e.respondWith(
      fetch(e.request)
        .then((r) => { caches.open(CACHE).then((c) => c.put("./index.html", r.clone())); return r; })
        .catch(() => caches.match("./index.html"))
    );
    return;
  }
  // Übrige eigene Dateien (Icons, Manifest): erst Cache, sonst Netz.
  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
});
