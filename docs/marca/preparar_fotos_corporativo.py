"""Fotos de /corporativo/ (16-11-2026): recorta, achica y guarda en WebP con nombre para Google.

Pedido de Diego: usar en venta corporativa las fotos NUEVAS de Tamara (las del
15-11-2026, copia en docs/marca/navidad-2026-origen/) en vez de las de AZA.

Las navideñas que ya estaban recortadas para /navidad/ se reutilizan tal cual
(regalos-de-navidad-dulcecita, box-navideno-bolsas-kraft); aca solo se generan
los recortes que faltaban.

Uso (desde la raiz del repo):
    python docs/marca/preparar_fotos_corporativo.py docs/marca/navidad-2026-origen BebesitaAPP/static/img
"""
import sys
from pathlib import Path

from PIL import Image

origen, destino = Path(sys.argv[1]), Path(sys.argv[2])

# archivo de origen -> (salida, caja de recorte (izq, arriba, der, abajo), tamaño final)
TRABAJOS = [
    # Segunda foto de la portada: la caja con ventana y el sticker rosado de Dulcecita.
    ("caja-cuchuflis-banados.jpeg", "galeria/caja-con-ventana-sticker-dulcecita.webp", (240, 0, 960, 1280), (540, 960)),
    # Portada fuera de temporada: las dos cajas con ventana, de cuerpo entero.
    ("cajas-con-ventana.jpeg", "galeria/cajas-dulcecita-con-ventana.webp", (0, 0, 960, 1280), (720, 960)),
    # Tarjeta "Box de regalo": la caja con ventana y el sticker azul.
    ("caja-cuchuflis-sin-bano.jpeg", "galeria/box-de-regalo-caja-con-ventana.webp", (0, 250, 960, 970), (960, 720)),
    # Tarjeta "Empaques con tu marca": cuchuflis embolsados uno a uno con sticker de la ocasion.
    ("dia-del-nino-barquillos.jpeg", "galeria/cuchuflis-con-sticker-personalizado.webp", (0, 180, 960, 900), (960, 720)),
    # Tarjeta "Eventos y pedidos por volumen": los regalos en fila dentro de su caja.
    ("navidad-regalos-en-fila.jpeg", "galeria/regalos-en-fila-con-cinta.webp", (0, 220, 720, 760), (720, 540)),
]

for nombre, salida, caja, tamano in TRABAJOS:
    with Image.open(origen / nombre) as im:
        pieza = im.convert("RGB").crop(caja).resize(tamano, Image.LANCZOS)
    ruta = destino / salida
    ruta.parent.mkdir(parents=True, exist_ok=True)
    pieza.save(ruta, "WEBP", quality=80, method=6)
    print(f"{salida:55} {tamano[0]}x{tamano[1]}  {ruta.stat().st_size // 1024} KB")
