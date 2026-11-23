"""El menú de escritorio cabe en todos los anchos (23-11-2026).

Uso:
    python menu_sin_desborde.py <base_url> [--rama <raiz_del_repo>]

- Sin --rama, mide el sitio tal cual.
- Con --rama, sirve el style.css DE ESA CARPETA en lugar del del sitio (intercepta la petición solo dentro de este
  navegador de prueba), igual que ficha_y_cabecera.py. Así se prueban los archivos exactos de la rama contra el sitio
  real sin desplegar nada.

Por qué existe: dos veces un enlace nuevo en el menú ("Arma tu box", después "Navidad") hizo que "Haz tu pedido" se
saliera de la pantalla. El 23-11 en 1366 px la página se corría 141 px hacia el lado y el logo quedaba cortado. Una
prueba de Django no ve eso: hay que medirlo en un navegador.

Comprueba en cada ancho y página:
  1. la página no tiene scroll lateral (scrollWidth == ancho de la ventana);
  2. "Haz tu pedido" termina dentro del contenedor del menú;
  3. el logo empieza dentro de la pantalla.
Sale con código 1 si algo falla. Solo lectura: abre páginas, no hace clic ni envía nada.
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/")
RAMA = Path(sys.argv[sys.argv.index("--rama") + 1]) if "--rama" in sys.argv else None
PAGINAS = ["/", "/navidad/", "/productos/"]
ANCHOS = [992, 1024, 1100, 1200, 1280, 1300, 1366, 1400, 1440, 1536, 1600, 1920]

MEDIR = """() => {
  const c = document.querySelector('.dr-nav .container'), cs = getComputedStyle(c), cr = c.getBoundingClientRect();
  const pedido = document.querySelector('a.dr-pedido').getBoundingClientRect();
  const logo = document.querySelector('.dr-brand').getBoundingClientRect();
  return {ventana: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth,
          pedido_der: Math.round(pedido.right), contenedor_der: Math.round(cr.right - parseFloat(cs.paddingRight)),
          logo_izq: Math.round(logo.left)};
}"""

fallas = 0
with sync_playwright() as p:
    nav = p.chromium.launch()
    css = (RAMA / "BebesitaAPP/static/css/style.css").read_text(encoding="utf-8") if RAMA else None
    print(f"modo: {'rama ' + str(RAMA) if RAMA else 'sitio'} · base: {BASE}")
    for ancho in ANCHOS:
        pg = nav.new_page(viewport={"width": ancho, "height": 800})
        if css:
            pg.route(re.compile(r".*/static/css/style(\.[0-9a-f]+)?\.css.*"),
                     lambda r: r.fulfill(body=css, content_type="text/css"))
        for ruta in PAGINAS:
            pg.goto(BASE + ruta, wait_until="load")
            pg.wait_for_timeout(600)  # el logo tiene transition .25s: medir después
            m = pg.evaluate(MEDIR)
            problemas = []
            if m["scroll"] > m["ventana"]:
                problemas.append(f"scroll lateral de {m['scroll'] - m['ventana']} px")
            if m["pedido_der"] > m["contenedor_der"] + 1:
                problemas.append(f"'Haz tu pedido' sale {m['pedido_der'] - m['contenedor_der']} px del contenedor")
            if m["logo_izq"] < 0:
                problemas.append(f"logo cortado {-m['logo_izq']} px")
            fallas += bool(problemas)
            print(f"{'FALLA' if problemas else 'ok   '} {ancho:>4} {ruta:<12} {'; '.join(problemas)}")
        pg.close()
    nav.close()

print(f"\n{fallas} combinación(es) con problemas")
sys.exit(1 if fallas else 0)
