"""Logo navideño de Dulcecita: el logotipo ORIGINAL + el gorro del diseño nuevo.

El PNG "transparente" que llego trae las letras redibujadas con un borde oscuro
(resto del fondo negro) y motas sueltas. El gorro, en cambio, esta bien. Aca se
recorta SOLO el gorro y se monta sobre el logo de siempre, en el mismo lugar y
a la misma escala: las letras quedan identicas a las del resto del año.

Uso: python -I componer_logo.py <navidad transparente> <logo actual> <carpeta salida>
"""
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

navidad = Image.open(sys.argv[1]).convert("RGBA")
actual = Image.open(sys.argv[2]).convert("RGBA")
salida = Path(sys.argv[3])
salida.mkdir(parents=True, exist_ok=True)

# --- 1. Escala y desplazamiento entre los dos logos -------------------------
# Las letras ocupan todo el alto en ambos: de la punta de la "l" a la base de
# "BAKERY". Con eso sale la escala; el borde izquierdo de la "d" da el origen.
caja_nav = navidad.getchannel("A").getbbox()          # incluye el gorro a la derecha
escala = actual.height / (caja_nav[3] - caja_nav[1])
origen_x, origen_y = caja_nav[0], caja_nav[1]
print("escala %.4f  origen (%d, %d)" % (escala, origen_x, origen_y))

# --- 2. Mascara del gorro ---------------------------------------------------
# Zona donde vive el gorro (medida en el archivo de 2048 px).
ZONA = (1560, 130, 1975, 410)
zona = navidad.crop(ZONA)
r, g, b, a = zona.split()


def es_rosado(pr, pg, pb):
    # El rosado de las letras es (245, 168, 214): rojo y azul altos, verde medio.
    # Incluye el rosado oscurecido por la sombra del gorro sobre la letra: esa
    # sombra pertenece a las letras redibujadas, no al gorro. El rojo del gorro
    # no entra (azul bajo) ni el pelo blanco o gris (rojo y verde parejos).
    return pr > 150 and pb > 120 and (pr - pg) > 25 and (pb - pg) > 8


pix = zona.load()
mascara = Image.new("L", zona.size, 0)
mpix = mascara.load()
for y in range(zona.height):
    for x in range(zona.width):
        pr, pg, pb, pa = pix[x, y]
        if pa > 128 and not es_rosado(pr, pg, pb):
            mpix[x, y] = 255

# Apertura: borra el borde oscuro de las letras (1-3 px) y las motas sueltas.
abierta = mascara.filter(ImageFilter.MinFilter(7)).filter(ImageFilter.MaxFilter(7))
abierta = ImageChops.multiply(abierta, mascara)

# Solo la pieza conectada con el gorro: se rellena desde un punto rojo del gorro.
semilla = (1760 - ZONA[0], 230 - ZONA[1])
assert abierta.getpixel(semilla) == 255, "la semilla no cae dentro del gorro"
relleno = abierta.copy()
ImageDraw.floodfill(relleno, semilla, 128)
gorro_mask = relleno.point(lambda v: 255 if v == 128 else 0)
# La apertura se come el pelo fino del borde: se recupera lo que toca al gorro.
cerca = gorro_mask.filter(ImageFilter.MaxFilter(5))
gorro_mask = ImageChops.lighter(gorro_mask, ImageChops.multiply(cerca, mascara))
# Cierre: tapa los agujeritos que dejan los brillos rosados dentro del gorro.
gorro_mask = gorro_mask.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))
# El borde del gorro trae 1-2 px oscuros del fondo negro original: se recortan.
gorro_mask = gorro_mask.filter(ImageFilter.MinFilter(5))

gorro = zona.copy()
gorro.putalpha(gorro_mask)
caja_gorro = gorro_mask.getbbox()
gorro = gorro.crop(caja_gorro)
gx, gy = ZONA[0] + caja_gorro[0], ZONA[1] + caja_gorro[1]
print("gorro", gorro.size, "en", (gx, gy))

# --- 3. Achicar con alfa premultiplicado (sin halo en el borde) --------------
nuevo = (round(gorro.width * escala), round(gorro.height * escala))
gorro_chico = gorro.convert("RGBa").resize(nuevo, Image.LANCZOS).convert("RGBA")
px, py = round((gx - origen_x) * escala), round((gy - origen_y) * escala)

# --- 4. Montar sobre el logo de siempre --------------------------------------
ancho = max(actual.width, px + gorro_chico.width)
arriba = max(0, -py)
lienzo = Image.new("RGBA", (ancho, actual.height + arriba), (0, 0, 0, 0))
lienzo.alpha_composite(actual, (0, arriba))
lienzo.alpha_composite(gorro_chico, (px, py + arriba))
print("logo con gorro", lienzo.size, "gorro en", (px, py + arriba))

# --- 4b. La misma caja que el logo de siempre --------------------------------
# El pompon sobresale por la derecha y el archivo quedaba mas ancho que el logo
# normal: en el menu eso empujaba todo 13 px y agrandaba un desborde que ya
# existia. Se achica el conjunto (7 %) para que quepa en la MISMA caja: el logo
# navideño ocupa exactamente el lugar del otro, en cualquier pantalla.
if lienzo.size != actual.size:
    factor = min(actual.width / lienzo.width, actual.height / lienzo.height)
    ajustado = lienzo.convert("RGBa").resize(
        (round(lienzo.width * factor), round(lienzo.height * factor)), Image.LANCZOS).convert("RGBA")
    caja = Image.new("RGBA", actual.size, (0, 0, 0, 0))
    caja.alpha_composite(ajustado, ((actual.width - ajustado.width) // 2, (actual.height - ajustado.height) // 2))
    lienzo = caja
    px = py = arriba = 0
print("logo final", lienzo.size)

lienzo.save(salida / "logo-dulcecita-navidad.png", optimize=True)
lienzo.save(salida / "logo-dulcecita-navidad.webp", quality=90, method=6)

# --- 5. Vistas para revisarlo a ojo ------------------------------------------
def sobre(im, color):
    fondo = Image.new("RGBA", im.size, color)
    fondo.alpha_composite(im)
    return fondo.convert("RGB")


sobre(lienzo, (255, 255, 255, 255)).save(salida / "vista_blanco.png")
sobre(lienzo, (42, 64, 87, 255)).save(salida / "vista_azul.png")
# Como se ve en el menu: 62 px de alto (escritorio) y 48 px (telefono), al doble.
for alto in (62, 48):
    chico = lienzo.resize((round(lienzo.width * alto * 2 / lienzo.height), alto * 2), Image.LANCZOS)
    sobre(chico, (255, 255, 255, 255)).save(salida / f"vista_menu_{alto}px_x2.png")
# El gorro al 300 % para ver el borde.
zoom = lienzo.crop((lienzo.width * 3 // 4, 0, lienzo.width, lienzo.height * 2 // 3))
zoom = zoom.resize((zoom.width * 3, zoom.height * 3), Image.LANCZOS)
sobre(zoom, (255, 255, 255, 255)).save(salida / "vista_gorro_x3.png")

for f in ("logo-dulcecita-navidad.png", "logo-dulcecita-navidad.webp"):
    print(f, (salida / f).stat().st_size, "bytes")
