"""Deja en produccion el catalogo que se armo en local (septiembre 2026).

La base de Render nacio de datadump.json, con el catalogo viejo (brownie,
tiramisu, alfajor blanco premium...). El catalogo nuevo, alfajores,
barquillos y cuchuflis con cobertura a eleccion, existia solo en la base local.

Corre en cada deploy, pero la carga es de UNA vez: si ya hay un producto con
estos nombres no toca nada, asi no pisa precios ni textos que la duena cambie
despues desde el admin. Los productos viejos se OCULTAN, no se borran: los
pedidos antiguos apuntan a ellos con CASCADE.

Lo que si repite en cada deploy es reponer la foto si falta: sin Cloudinary
el disco de Render se borra en cada despliegue y la tarjeta quedaria sin foto.
"""
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from BebesitaAPP.models import CategoriaProducto, Opcion, Producto

FOTOS = Path(__file__).resolve().parents[2] / "catalogo_inicial"

CATALOGO = [
    {
        "nombre": "Barquillos Rellenos Bañados en Chocolate",
        "descripcion": (
            "Barquillos crujientes rellenos de cremoso manjar y bañados en chocolate en sus "
            "extremos. Una combinación equilibrada de texturas y sabores, perfecta para "
            "acompañar un café o disfrutar en cualquier momento."
        ),
        "precio": 1290, "orden": 0, "unidades_por_pack": 1, "foto": "barquillos-puntas.jpg",
    },
    {
        "nombre": "Alfajores",
        "descripcion": (
            "Alfajor de triple capa: galletas suaves, relleno cremoso de manjar y cobertura "
            "de chocolate. Elige la cobertura al pedir."
        ),
        "precio": 1590, "orden": 1, "unidades_por_pack": 1, "foto": "alfajor-chocolate-negro.jpg",
    },
    {
        "nombre": "Cuchuflís bañados",
        "descripcion": (
            "Cuchuflís crujientes rellenos de manjar y bañados enteros en chocolate. "
            "Se venden en bolsita de 4 unidades."
        ),
        "precio": 1590, "orden": 3, "unidades_por_pack": 4, "foto": "cuchuflis-bolsita.jpg",
    },
    {
        # Sin baño y sin cobertura a elegir: por eso es mas barato y va aparte.
        "nombre": "Cuchuflís rellenos",
        "descripcion": (
            "Cuchuflís crujientes rellenos de manjar, sin baño de chocolate. "
            "Se venden en bolsita de 4 unidades."
        ),
        "precio": 1190, "orden": 4, "unidades_por_pack": 4, "foto": "cuchuflis-rellenos.jpg",
        "sin_cobertura": True,
    },
]

COBERTURAS = [("Chocolate", "#5b3a29", 1), ("Chocolate blanco", "#f3ead9", 2)]


class Command(BaseCommand):
    help = "Carga una vez el catalogo de alfajores, barquillos y cuchuflis y oculta el viejo."

    def handle(self, *args, **options):
        nombres = [item["nombre"] for item in CATALOGO]
        principales = Producto.objects.filter(variante_de__isnull=True)

        if principales.filter(nombre__in=nombres).exists():
            self.stdout.write("Catalogo nuevo ya cargado: no se toca.")
        else:
            self._cargar(nombres)

        self._reponer_fotos(principales.filter(nombre__in=nombres))
        self._torta_cuchuflis()

    @transaction.atomic
    def _torta_cuchuflis(self):
        """Torta de cuchuflis (15-09-2026): se crea una vez si no existe.

        Precio fijo por tamaño y cobertura (no es base + recargo parejo):
        50 sin cobertura 14.990 / con 17.990, 100 sin 29.990 / con 34.990.
        """
        from BebesitaAPP.models import PrecioCombinacion, ProductoImagen

        nombre = "Torta de cuchuflís"
        if Producto.objects.filter(nombre=nombre).exists():
            return
        categoria, _ = CategoriaProducto.objects.get_or_create(
            slug="dulce", defaults={"nombre": "Dulce", "orden": 1, "activa": True})
        t50 = Opcion.objects.get_or_create(tipo="tamano", nombre="50 cuchuflís", defaults={"orden": 1})[0]
        t100 = Opcion.objects.get_or_create(tipo="tamano", nombre="100 cuchuflís", defaults={"orden": 2})[0]
        sin = Opcion.objects.get_or_create(tipo="cobertura", nombre="Sin cobertura",
                                           defaults={"color": "#e8c98f", "orden": 0})[0]
        choc = Opcion.objects.get_or_create(tipo="cobertura", nombre="Chocolate",
                                            defaults={"color": "#5b3a29", "orden": 1})[0]
        blanco = Opcion.objects.get_or_create(tipo="cobertura", nombre="Chocolate blanco",
                                              defaults={"color": "#f3ead9", "orden": 2})[0]
        torta = Producto(
            nombre=nombre, precio=14990, categoria=categoria, destacado=True, visible=True,
            disponible=True, orden=5, unidades_por_pack=1, minimo=1, en_box=False, pide_nota=True,
            descripcion=("Torta armada con cuchuflís rellenos de manjar, en 50 o 100 unidades, "
                         "sin cobertura o bañados en chocolate. Terminada con cinta y decoración "
                         "a tu gusto: cuéntanos los colores al hacer el pedido."),
        )
        self._poner_foto(torta, "torta-cuchuflis.jpg")
        torta.save()
        torta.opciones.add(t50, t100, sin, choc, blanco)
        for tam, cob, precio in [(t50, sin, 14990), (t50, choc, 17990), (t50, blanco, 17990),
                                 (t100, sin, 29990), (t100, choc, 34990), (t100, blanco, 34990)]:
            pc = PrecioCombinacion.objects.create(producto=torta, precio=precio)
            pc.opciones.set([tam, cob])
            pc.actualizar_clave()
        for extra in ["torta-cuchuflis-2.jpg", "torta-cuchuflis-3.jpg", "torta-cuchuflis-4.jpg"]:
            img = ProductoImagen(producto=torta)
            with open(FOTOS / extra, "rb") as archivo:
                img.imagen.save(extra, File(archivo), save=True)
        self.stdout.write(self.style.SUCCESS("Torta de cuchuflís creada con 6 precios."))

    @transaction.atomic
    def _cargar(self, nombres):
        categoria, _ = CategoriaProducto.objects.get_or_create(
            slug="dulce", defaults={"nombre": "Dulce", "orden": 1, "activa": True})
        coberturas = [
            Opcion.objects.get_or_create(tipo="cobertura", nombre=n, defaults={"color": c, "orden": o})[0]
            for n, c, o in COBERTURAS
        ]

        ocultos = Producto.objects.exclude(nombre__in=nombres).update(visible=False, destacado=False)

        for item in CATALOGO:
            producto = Producto(
                nombre=item["nombre"], descripcion=item["descripcion"], precio=item["precio"],
                categoria=categoria, destacado=True, visible=True, disponible=True,
                orden=item["orden"], unidades_por_pack=item["unidades_por_pack"],
            )
            self._poner_foto(producto, item["foto"])
            producto.save()
            if not item.get("sin_cobertura"):
                producto.opciones.add(*coberturas)

        self.stdout.write(self.style.SUCCESS(
            f"Catalogo nuevo cargado: {len(CATALOGO)} productos, {ocultos} viejos ocultos."))

    def _reponer_fotos(self, productos):
        fotos = {item["nombre"]: item["foto"] for item in CATALOGO}
        for producto in productos:
            foto = fotos[producto.nombre]
            # Solo si sigue siendo la foto de fabrica: si la duena subio otra, es suya.
            if Path(producto.imagen.name or "").stem.split("_")[0] != Path(foto).stem:
                continue
            try:
                existe = producto.imagen.storage.exists(producto.imagen.name)
            except Exception:
                existe = True  # si no se puede consultar, mejor no resubir a ciegas
            if not existe:
                self._poner_foto(producto, foto)
                producto.save(update_fields=["imagen"])
                self.stdout.write(f"Foto repuesta: {producto.nombre}")

    @staticmethod
    def _poner_foto(producto, foto):
        with open(FOTOS / foto, "rb") as archivo:
            producto.imagen.save(foto, File(archivo), save=False)
