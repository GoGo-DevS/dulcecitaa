"""Regresión visual de la ficha y la cabecera (20-11-2026).

Uso:
    python ficha_y_cabecera.py <base_url> <carpeta_salida> [--rama <raiz_del_repo>]

- Sin --rama, mide el sitio tal cual (antes).
- Con --rama, sirve style.css y main.js DE ESA CARPETA en lugar de los del sitio (intercepta las peticiones solo dentro
  de este navegador de prueba) y agrega la clase --pagina que pone la plantilla. Es la forma de probar los archivos
  exactos de la rama contra datos reales sin desplegar nada.

Solo lectura: no hace clic en el carrito ni envía formularios. Abre el modal (GET ?modal=1) y el menú móvil.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/")
OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
RAMA = Path(sys.argv[sys.argv.index("--rama") + 1]) if "--rama" in sys.argv else None
ANCHOS = [(1440, 900, False), (1024, 768, False), (820, 1180, True), (390, 844, True)]

sitemap = urllib.request.urlopen(urllib.request.Request(f"{BASE}/sitemap.xml", headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read().decode()
FICHAS = [u for u in re.findall(r"<loc>([^<]+)</loc>", sitemap) if re.search(r"/productos/[^/]+/$", u)]

MEDIR = """() => {
  const q = s => document.querySelector(s);
  const box = el => el ? el.getBoundingClientRect() : null;
  const wrap = q('.product-detail-wrap'), img = q('.product-detail-media img'), cont = q('.product-detail-content');
  const acts = q('.detail-actions');
  // último bloque de contenido antes de los botones
  let prev = acts ? acts.previousElementSibling : null;
  while (prev && prev.getBoundingClientRect().height === 0) prev = prev.previousElementSibling;
  const w = box(wrap), a = box(acts), p = box(prev), i = box(img);
  return {wrap_h: w && Math.round(w.height), img_h: i && Math.round(i.height),
          hueco: (a && p) ? Math.round(a.top - p.bottom) : null,
          botones_dentro: (a && w) ? (a.bottom <= w.bottom + 1) : null,
          desborde_horizontal: document.documentElement.scrollWidth > innerWidth + 1};
}"""


def preparar(pg):
    if not RAMA:
        return
    css = (RAMA / "BebesitaAPP/static/css/style.css").read_text(encoding="utf-8")
    js = (RAMA / "BebesitaAPP/static/js/main.js").read_text(encoding="utf-8")
    pg.route(re.compile(r".*/static/css/style(\.[0-9a-f]+)?\.css.*"), lambda r: r.fulfill(body=css, content_type="text/css"))
    pg.route(re.compile(r".*/static/js/main(\.[0-9a-f]+)?\.js.*"), lambda r: r.fulfill(body=js, content_type="application/javascript"))


def clase_pagina(pg):
    if RAMA:  # lo que hace la plantilla de la rama con es_pagina=True
        pg.evaluate("document.querySelector('.product-detail-wrap')?.classList.add('product-detail-wrap--pagina')")


res = {"modo": "rama" if RAMA else "sitio", "base": BASE, "fichas": {}, "cabecera": {}, "modal": {}, "menu": {}}
with sync_playwright() as p:
    b = p.chromium.launch()
    for (w, h, movil) in ANCHOS:
        ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=movil, has_touch=movil)
        pg = ctx.new_page(); preparar(pg)
        for url in FICHAS:
            slug = url.rstrip("/").split("/")[-1]
            pg.goto(url, wait_until="networkidle"); clase_pagina(pg)
            pg.add_style_tag(content=".reveal-item{opacity:1!important;transform:none!important;transition:none!important}.nieve{display:none!important}")
            pg.wait_for_timeout(300)
            res["fichas"][f"{slug}@{w}"] = pg.evaluate(MEDIR)
            if w in (1440, 390):
                pg.locator(".product-detail-wrap").screenshot(path=str(OUT / f"{slug}-{w}.png"))
        # cabecera: barrido alrededor del umbral, ida y vuelta
        pg.goto(FICHAS[0], wait_until="networkidle"); pg.wait_for_timeout(400)
        pg.evaluate("""() => { window.__t = 0; const c = document.querySelector('.dr-cabecera');
          new MutationObserver(() => window.__t++).observe(c, {attributes: true, attributeFilter: ['class']}); }""")
        for y in list(range(96, 200, 4)) + list(range(200, 0, -8)):
            pg.evaluate(f"window.scrollTo(0, {y})"); pg.wait_for_timeout(350)
        res["cabecera"][w] = pg.evaluate("window.__t")
        # menú móvil con la cabecera encogida
        if movil and w == 390:
            pg.evaluate("window.scrollTo(0, 500)"); pg.wait_for_timeout(500)
            pg.click(".navbar-toggler"); pg.wait_for_timeout(600)
            abierto = pg.evaluate("document.querySelector('#navbarMain').classList.contains('show')")
            visibles = pg.evaluate("[...document.querySelectorAll('#navbarMain .nav-link')].filter(a => a.getBoundingClientRect().height > 0).length")
            pg.click(".navbar-toggler"); pg.wait_for_timeout(600)
            cerrado = not pg.evaluate("document.querySelector('#navbarMain').classList.contains('show')")
            res["menu"][w] = {"abre": abierto, "enlaces_visibles": visibles, "cierra": cerrado}
        ctx.close()
    # modal de escritorio: los botones siguen pegados abajo
    ctx = b.new_context(viewport={"width": 1440, "height": 900}); pg = ctx.new_page(); preparar(pg)
    pg.goto(f"{BASE}/productos/", wait_until="networkidle")
    tarjeta = pg.locator("[data-bs-target='#modalProducto'], [data-catalog-card] a, [data-catalog-card]").first
    try:
        tarjeta.click(); pg.wait_for_selector("#modalProducto .detail-actions", state="visible", timeout=8000); pg.wait_for_timeout(800)
        res["modal"] = pg.evaluate("""() => { const a = document.querySelector('#modalProducto .detail-actions').getBoundingClientRect();
            const c = document.querySelector('#modalProducto .product-detail-content').getBoundingClientRect();
            return {pegado_abajo: Math.abs(c.bottom - a.bottom) < 2, posicion: getComputedStyle(document.querySelector('#modalProducto .detail-actions')).position,
                    tiene_clase_pagina: !!document.querySelector('#modalProducto .product-detail-wrap--pagina')}; }""")
        pg.locator("#modalProducto").screenshot(path=str(OUT / "modal-1440.png"))
    except Exception as e:
        res["modal"] = {"error": repr(e)[:200]}
    ctx.close(); b.close()
(OUT / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k != "fichas"}, ensure_ascii=False))
