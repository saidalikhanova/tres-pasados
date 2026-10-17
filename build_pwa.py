"""Собирает PWA-версию тренажёра в папку docs/ из index.html (того же файла, что публикуется как artifact).

Запуск:  python3 build_pwa.py
Потом закоммитить и запушить папку docs/ — GitHub Pages обновится сам.
"""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).parent
OUT = ROOT / "docs"
OUT.mkdir(exist_ok=True)
(OUT / "icons").mkdir(exist_ok=True)

page = (ROOT / "index.html").read_text(encoding="utf-8")

# ---------- иконка: временная шкала, как в книге ----------
# синяя точка — indefinido (событие), бирюзовая полоса — imperfecto (длилось),
# фиолетовая точка у стрелки «сейчас» — perfecto (связь с настоящим)
INK = (24, 32, 58)
LINE = (214, 220, 232)
IND, IMP, PER = (92, 130, 245), (32, 178, 172), (163, 116, 240)


def icon(size: int, safe: float) -> Image.Image:
    """safe — доля стороны, внутри которой рисуем (для maskable нужен запас по краям)."""
    scale = 4
    s = size * scale
    img = Image.new("RGB", (s, s), INK)
    d = ImageDraw.Draw(img)
    box = s * safe
    x0, x1 = (s - box) / 2, (s + box) / 2
    cy = s / 2
    lw = box * 0.035
    # линия времени со стрелкой
    d.rounded_rectangle([x0, cy - lw / 2, x1 - box * 0.06, cy + lw / 2], radius=lw / 2, fill=LINE)
    ah = box * 0.11
    d.polygon([(x1, cy), (x1 - ah * 1.2, cy - ah), (x1 - ah * 1.2, cy + ah)], fill=LINE)
    # imperfecto — длительность
    bh = box * 0.13
    d.rounded_rectangle([x0 + box * 0.27, cy - bh / 2, x0 + box * 0.58, cy + bh / 2], radius=bh / 2, fill=IMP)
    # indefinido — точка в прошлом, perfecto — у «сейчас»
    r = box * 0.085
    for cx, col in ((x0 + box * 0.09, IND), (x0 + box * 0.76, PER)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    return img.resize((size, size), Image.LANCZOS)


icon(192, 0.80).save(OUT / "icons/icon-192.png")
icon(512, 0.80).save(OUT / "icons/icon-512.png")
icon(512, 0.64).save(OUT / "icons/maskable-512.png")
icon(180, 0.80).save(OUT / "icons/apple-touch-icon.png")

# ---------- manifest ----------
manifest = {
    "name": "Tres pasados",
    "short_name": "Tres pasados",
    "description": "Тренажёр испанских прошедших времён по Vitamina B1",
    "lang": "ru",
    "start_url": "./",
    "scope": "./",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#EEF1F6",
    "theme_color": "#18203A",
    "icons": [
        {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
        {"src": "icons/maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}
(OUT / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------- index.html: оборачиваем страницу artifact в полноценный документ ----------
head = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#EEF1F6" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#11151F" media="(prefers-color-scheme: dark)">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Tres pasados">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icons/icon-192.png" type="image/png">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<style>
  /* то, что в artifact добавляет платформа: сброс и отступы под вырез экрана */
  :root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
  body{margin:0;font:14px system-ui,-apple-system,sans-serif;-webkit-text-size-adjust:100%}
  img{max-width:100%}
  [hidden]{display:none!important}
</style>
"""
tail = """
<script>
if('serviceWorker' in navigator){
  window.addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{}));
}
</script>
</body>
</html>
"""
# <title>, шрифты и <style> из artifact идут в <head>, остальное — в <body>
split = page.index("</style>") + len("</style>")
html = head + page[:split] + "\n</head>\n<body>\n" + page[split:] + tail
(OUT / "index.html").write_text(html, encoding="utf-8")

# ---------- service worker: версия = хеш содержимого, чтобы обновления доходили ----------
files = ["./", "index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png",
         "icons/maskable-512.png", "icons/apple-touch-icon.png"]
digest = hashlib.sha256()
for f in files[1:]:
    digest.update((OUT / f).read_bytes())
version = digest.hexdigest()[:10]

sw = f"""// Tres pasados — офлайн-режим. Версия меняется при каждой сборке.
const CACHE = 'tres-pasados-{version}';
const SHELL = {json.dumps(files)};

self.addEventListener('install', e => {{
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
}});

self.addEventListener('activate', e => {{
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('tres-pasados-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
}});

self.addEventListener('fetch', e => {{
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // страница: сначала сеть (чтобы приходили обновления), без сети — из кэша
  if (req.mode === 'navigate') {{
    e.respondWith(fetch(req).then(res => {{
      const copy = res.clone(); caches.open(CACHE).then(c => c.put('index.html', copy)); return res;
    }}).catch(() => caches.match('index.html')));
    return;
  }}

  // шрифты Google: из кэша, в фоне обновляем
  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') {{
    e.respondWith(caches.open(CACHE).then(async c => {{
      const hit = await c.match(req);
      const net = fetch(req).then(res => {{ c.put(req, res.clone()); return res; }}).catch(() => hit);
      return hit || net;
    }}));
    return;
  }}

  // остальные файлы приложения: кэш, потом сеть
  if (url.origin === location.origin) {{
    e.respondWith(caches.match(req).then(hit => hit || fetch(req)));
  }}
}});
"""
(OUT / "sw.js").write_text(sw, encoding="utf-8")
(OUT / ".nojekyll").write_text("", encoding="utf-8")
print("PWA собрана в", OUT, "версия", version)
