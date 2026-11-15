"""Fotos de /navidad/ (15-11-2026): recorta, achica y guarda en WebP con nombre para Google.

Origen: las fotos que mando Tamara por WhatsApp el 15-11-2026 (copia en
docs/marca/navidad-2026-origen/). Las tres navideñas son sus regalos en bolsa
kraft con cinta roja y verde y tarjeta de "Feliz Navidad"; la de las dos cajas
con ventana muestra cuchuflis bañados y sin baño.

La foto del Dia del Nino NO se usa en /navidad/: el sticker dice otra fecha.

Uso (desde la raiz del repo):
    python docs/marca/preparar_fotos_navidad.py docs/marca/navidad-2026-origen BebesitaAPP/static/img
"""
import sys
from pathlib import Path

from PIL import Image

origen, destino = Path(sys.argv[1]), Path(sys.argv[2])

# archivo de origen -> (salida, caja de recorte (izq, arriba, der, abajo), tamaño final, formato)
TRABAJOS = [
    # Portada: la caja llena de regalos con cinta roja y verde.
    ("navidad-caja-de-regalos.jpeg", "galeria/regalos-de-navidad-dulcecita.webp", (0, 200, 720, 1160), (720, 960), "WEBP"),
    # Segunda foto de la portada: los regalos en fila, con su tarjeta.
    ("navidad-regalos-en-fila.jpeg", "galeria/regalo-navideno-cinta-y-tarjeta.webp", (0, 0, 720, 1280), (540, 960), "WEBP"),
    # Tarjeta del box navideño: bolsas con cinta verde y tarjeta, desde arriba.
    ("navidad-bolsas-desde-arriba.jpeg", "galeria/box-navideno-bolsas-kraft.webp", (0, 330, 960, 1050), (960, 720), "WEBP"),
    # Tarjeta de los dulces por unidad: las dos cajas con ventana.
    ("cajas-con-ventana.jpeg", "galeria/cajas-cuchuflis-para-regalar.webp", (0, 300, 960, 1020), (960, 720), "WEBP"),
    # Imagen al compartir /navidad/ por WhatsApp o Instagram (1200x630, JPEG).
    ("navidad-caja-de-regalos.jpeg", "og-navidad.jpg", (0, 560, 720, 938), (1200, 630), "JPEG"),
]

for nombre, salida, caja, tamano, formato in TRABAJOS:
    with Image.open(origen / nombre) as im:
        pieza = im.convert("RGB").crop(caja).resize(tamano, Image.LANCZOS)
    ruta = destino / salida
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if formato == "WEBP":
        pieza.save(ruta, "WEBP", quality=80, method=6)
    else:
        pieza.save(ruta, "JPEG", quality=84, optimize=True, progressive=True)
    print(f"{salida:55} {tamano[0]}x{tamano[1]}  {ruta.stat().st_size // 1024} KB")
