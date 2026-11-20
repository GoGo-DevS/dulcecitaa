"""Productos de la tienda web, desde el panel (15-11-2026).

Hasta hoy el catalogo de dulcecita.cl solo se editaba en /admin/. La duena no
lo usa, asi que cada cambio de precio, de foto o de minimo pasaba por Diego y
por un deploy. Esta seccion le deja hacerlo a ella, desde el telefono.

Reglas que vienen de errores caros:
- Un producto CON historia no se borra nunca: las lineas de los pedidos de la
  web apuntan a el con CASCADE y borrarlo se llevaria esos pedidos (plata). Si
  tiene pedidos de la web, cajas o componentes de pedidos del panel o un costo
  cargado, "Eliminar" lo ARCHIVA: oculto, fuera de Google, con todo guardado.
- Uno SIN historia (los duplicados recien creados) si se borra (20-11-2026),
  con sus fotos, precios por combinacion y variantes, y su direccion vieja
  queda redirigiendo con 301 a donde se elija (RedireccionProducto).
- La direccion web (slug) no se edita: cambiarla rompe los enlaces compartidos
  y lo que Google ya tiene indexado.
- Despues de guardar se dice en pesos que cambio ("$1.590 -> $350"): un precio
  mal publicado es el error mas caro de una tienda, y el que lo escribio tiene
  que poder verlo al tiro.
"""
from django import forms
from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Max, ProtectedError, RestrictedError
from django.db.models.deletion import Collector
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from BebesitaAPP import fichas_seo
from BebesitaAPP.models import CarritoItem, Opcion
from BebesitaAPP.models import PedidoItem as LineaPedidoWeb
from BebesitaAPP.models import (PrecioCombinacion, PreguntaFrecuente, Producto, ProductoImagen, Promocion,
                                RedireccionProducto)

from .forms import ProductoForm, achicar_foto
from .models import Componente, CostoProducto
from .models import PedidoItem as CajaPedidoPanel

_ORDEN_TIPOS = {tipo: i for i, (tipo, _) in enumerate(Opcion.TIPOS)}


def _pesos(valor):
    return "$" + fichas_seo._pesos(valor)


def como_se_cobra(producto):
    """"$350 por unidad", "$1.590 la bolsita de 4" o "desde $14.990 (4 precios)".

    Precio de LISTA, sin la promocion: en el panel la duena edita el precio
    normal; el descuento de una campaña se ve en Promos.
    """
    combos = list(producto.precios_combinacion.all())
    if combos:
        cuantos = len(combos)
        return f"desde {_pesos(min(c.precio for c in combos))} ({cuantos} precio{'s' if cuantos != 1 else ''})"
    return f"{_pesos(producto.precio)} {fichas_seo.unidad_de_venta(producto)}"


def _nombre_combo(combo):
    """"50 cuchuflís · Sin cobertura": el tamaño primero, como en la web."""
    opciones = sorted(combo.opciones.all(), key=lambda op: (_ORDEN_TIPOS.get(op.tipo, 9), op.orden, op.nombre))
    return " · ".join(op.nombre for op in opciones) or "Sin opciones"


def _principales():
    return (Producto.objects.filter(variante_de__isnull=True)
            .prefetch_related("opciones", "precios_combinacion"))


def productos_lista(request):
    productos = list(_principales().order_by("orden", "nombre"))
    for p in productos:
        p.cobro = como_se_cobra(p)
        p.minimo_real = p.minimo_efectivo()
    return render(request, "gestion/productos_lista.html", {
        "en_web": [p for p in productos if p.visible],
        "ocultos": [p for p in productos if not p.visible],
        "promo": Promocion.vigente(),
    })


def _leer_combos(datos, combos):
    """Los precios por combinacion que vienen en el formulario.

    Devuelve ([(combo, precio nuevo)], [errores]). Solo se editan los que ya
    existen: crear una combinacion nueva es armar un producto, y eso se hace
    con Diego.
    """
    leidos, errores = [], []
    for combo in combos:
        crudo = (datos.get(f"combo_{combo.pk}") or "").strip().replace(".", "").replace("$", "")
        if not crudo.isdigit() or int(crudo) <= 0:
            errores.append(f"{combo.nombre}: escribe un precio mayor que cero.")
            combo.valor = datos.get(f"combo_{combo.pk}", "")
            continue
        combo.valor = int(crudo)
        leidos.append((combo, int(crudo)))
    return leidos, errores


def _cambios(antes, producto):
    """Lo que cambio, en palabras y en pesos, para el aviso de despues de guardar."""
    cambios = []
    if antes["precio"] != producto.precio:
        cambios.append(f"precio {_pesos(antes['precio'])} → {_pesos(producto.precio)}")
    if antes["unidades_por_pack"] != producto.unidades_por_pack:
        cambios.append("ahora se vende " + ("por unidad" if producto.unidades_por_pack == 1
                                           else f"en paquete de {producto.unidades_por_pack}"))
    if antes["minimo"] != producto.minimo:
        cambios.append(f"mínimo {producto.minimo_efectivo()}")
    if antes["visible"] != producto.visible:
        cambios.append("ahora se ve en la web" if producto.visible else "ya no se ve en la web")
    if antes["disponible"] != producto.disponible:
        cambios.append("se puede comprar" if producto.disponible else "quedó como no disponible")
    return cambios


MAX_FOTOS_EXTRA = 8


def _cuantos(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


def _y(partes):
    """["a", "b", "c"] -> "a, b y c"."""
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]


def _leer_fotos_extra(request, producto):
    """Las fotos extra que se suben y las que se marcan para quitar (20-11-2026).

    Devuelve (fotos nuevas ya achicadas, ids a quitar, errores). Cada foto pasa
    por achicar_foto, igual que la principal: una foto de celular de 6 MB y
    4.000 px no se guarda tal cual. Solo se pueden quitar fotos de ESTE producto.
    """
    actuales = set(producto.imagenes.values_list("pk", flat=True)) if producto else set()
    quitar = {int(x) for x in request.POST.getlist("quitar_foto") if x.isdigit()} & actuales
    archivos = [archivo for archivo in request.FILES.getlist("fotos_extra") if archivo]
    if len(actuales) - len(quitar) + len(archivos) > MAX_FOTOS_EXTRA:
        return [], quitar, [f"Caben hasta {MAX_FOTOS_EXTRA} fotos extra por producto. Quita alguna o sube menos."]
    nuevas, errores = [], []
    for archivo in archivos:
        if archivo.size > ProductoForm.FOTO_PESO_MAXIMO:
            errores.append(f"«{archivo.name}» pesa demasiado (máximo 12 MB).")
            continue
        try:
            nuevas.append(achicar_foto(archivo, ProductoForm.FOTO_LADO_MAXIMO))
        except forms.ValidationError as error:
            errores.append(f"«{archivo.name}»: {error.messages[0]}")
    return nuevas, quitar, errores


def _guardar_fotos_extra(producto, nuevas, quitar):
    """Quita las marcadas y agrega las nuevas al final. Devuelve lo que cambio, en palabras.

    Se borra la fila, no el archivo: la foto sigue en el almacenamiento por si
    hubo un error (un archivo de un cliente nunca vive en una sola copia).
    """
    cambios = []
    if quitar:
        quitadas, _ = ProductoImagen.objects.filter(producto=producto, pk__in=quitar).delete()
        cambios.append(_cuantos(quitadas, "foto extra quitada", "fotos extra quitadas"))
    for foto in nuevas:
        ProductoImagen.objects.create(producto=producto, imagen=foto)
    if nuevas:
        cambios.append(_cuantos(len(nuevas), "foto extra agregada", "fotos extra agregadas"))
    return cambios


def producto_form(request, pk=None):
    producto = get_object_or_404(Producto, pk=pk, variante_de__isnull=True) if pk else None
    combos = list(producto.precios_combinacion.prefetch_related("opciones")) if producto else []
    for combo in combos:
        combo.nombre = _nombre_combo(combo)
        combo.valor = combo.precio
    # Antes de armar el formulario: validar un ModelForm ya escribe sobre la instancia.
    antes = ({campo: getattr(producto, campo) for campo in
              ("precio", "unidades_por_pack", "minimo", "visible", "disponible")} if producto else None)
    errores_combos, errores_fotos = [], []

    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        precios_combo, errores_combos = _leer_combos(request.POST, combos)
        fotos_nuevas, quitar_fotos, errores_fotos = _leer_fotos_extra(request, producto)
        if form.is_valid() and not errores_combos and not errores_fotos:
            with transaction.atomic():
                guardado = form.save()
                cambios = _cambios(antes, guardado) if antes else []
                for combo, nuevo in precios_combo:
                    if combo.precio != nuevo:
                        cambios.append(f"{combo.nombre}: {_pesos(combo.precio)} → {_pesos(nuevo)}")
                        combo.precio = nuevo
                        combo.save(update_fields=["precio"])
                cambios += _guardar_fotos_extra(guardado, fotos_nuevas, quitar_fotos)
            if not antes:
                con_fotos = (f", con {_cuantos(len(fotos_nuevas), 'foto extra', 'fotos extra')}"
                             if fotos_nuevas else "")
                messages.success(request, f"«{guardado.nombre}» creado: {como_se_cobra(guardado)}, "
                                          f"desde {guardado.minimo_efectivo()}{con_fotos}.")
            elif cambios:
                messages.success(request, f"«{guardado.nombre}» guardado: {'; '.join(cambios)}.")
            else:
                messages.success(request, f"«{guardado.nombre}» guardado.")
            if guardado.visible:
                messages.info(request, "El cambio ya está en la web.")
            return redirect("gestion:productos")
    else:
        inicial = {}
        if not producto:
            ultimo = Producto.objects.filter(variante_de__isnull=True).aggregate(m=Max("orden"))["m"]
            inicial = {"orden": (ultimo or 0) + 1, "visible": True, "disponible": True}
        form = ProductoForm(instance=producto, initial=inicial)

    return render(request, "gestion/producto_form.html", {
        "form": form,
        "producto": producto,
        "combos": combos,
        "errores_combos": errores_combos,
        "errores_fotos": errores_fotos,
        # En el orden en que se subieron: es el orden de la ficha publica.
        "fotos_extra": list(producto.imagenes.order_by("pk")) if producto else [],
        "max_fotos_extra": MAX_FOTOS_EXTRA,
        "titulo": f"Editar {producto.nombre}" if producto else "Nuevo producto",
        "cobro": como_se_cobra(producto) if producto else "",
        "promo": Promocion.vigente(),
        "minimo_general": max(1, int(getattr(settings, "MINIMO_UNIDADES", 1))),
    })


@require_POST
def producto_toggle(request, pk, campo):
    """Mostrar u ocultar, y marcar disponible o no, sin abrir el formulario."""
    if campo not in ("visible", "disponible"):
        return redirect("gestion:productos")
    producto = get_object_or_404(Producto, pk=pk, variante_de__isnull=True)
    setattr(producto, campo, not getattr(producto, campo))
    producto.save(update_fields=[campo])
    if campo == "visible":
        if producto.visible:
            messages.success(request, f"«{producto.nombre}» ya se ve en la web.")
        else:
            messages.info(request, f"«{producto.nombre}» quedó oculto: sale del catálogo, "
                                   "pero los pedidos anteriores no se pierden.")
    elif producto.disponible:
        messages.success(request, f"«{producto.nombre}» se puede comprar otra vez.")
    else:
        messages.info(request, f"«{producto.nombre}» quedó como no disponible: se ve, pero no se puede comprar.")
    return redirect("gestion:productos")


# --- Eliminar o archivar (20-11-2026) -----------------------------------------
# Tamara no podia borrar y por eso creaba duplicados (pan-de-pascua-2,
# torta-de-cuchuflis-2). Borrar un producto con ventas se llevaria las lineas
# de los pedidos de la web (CASCADE): la regla es borrar SOLO lo que no tiene
# ninguna historia, y archivar todo lo demas.

def _familia(producto):
    """Los ids del producto y de todas sus variantes (y las variantes de esas)."""
    ids, frontera = {producto.pk}, {producto.pk}
    while frontera:
        frontera = set(Producto.objects.filter(variante_de_id__in=frontera)
                       .exclude(pk__in=ids).values_list("pk", flat=True))
        ids |= frontera
    return ids


def historial(producto):
    """Por que este producto NO se puede borrar, en palabras. Lista vacia = se puede.

    Cuenta tambien sus variantes: borrar el principal se lleva las variantes, y
    con ellas las lineas de pedido que las compraron.
    """
    ids = _familia(producto)
    motivos = []
    web = LineaPedidoWeb.objects.filter(producto_id__in=ids).values("pedido_id").distinct().count()
    if web:
        motivos.append(f"está en {_cuantos(web, 'pedido', 'pedidos')} de la web")
    cajas = CajaPedidoPanel.objects.filter(producto_id__in=ids).values("pedido_id").distinct().count()
    if cajas:
        motivos.append(f"es la caja de {_cuantos(cajas, 'pedido', 'pedidos')} del panel")
    dentro = Componente.objects.filter(producto_id__in=ids).values("item__pedido_id").distinct().count()
    if dentro:
        motivos.append(f"va dentro de las cajas de {_cuantos(dentro, 'pedido', 'pedidos')} del panel")
    if CostoProducto.objects.filter(producto_id__in=ids).exists():
        motivos.append("tiene su costo por unidad cargado")
    return motivos


def lo_que_se_va(producto):
    """Lo que se borra junto con un producto sin historia, en palabras."""
    ids = _familia(producto)
    cuentas = (
        (ProductoImagen.objects.filter(producto_id__in=ids).count(), "foto extra", "fotos extra"),
        (PrecioCombinacion.objects.filter(producto_id__in=ids).count(),
         "precio por combinación", "precios por combinación"),
        (len(ids) - 1, "variante", "variantes"),
        (PreguntaFrecuente.objects.filter(producto_id__in=ids).count(),
         "pregunta frecuente de su ficha", "preguntas frecuentes de su ficha"),
        (CarritoItem.objects.filter(producto_id__in=ids).count(),
         "línea de un carrito guardado", "líneas de carritos guardados"),
    )
    return [_cuantos(n, singular, plural) for n, singular, plural in cuentas if n]


# Lo UNICO que puede irse junto con un producto sin historia.
_SE_VAN_CON_EL = {Producto, ProductoImagen, PrecioCombinacion, PreguntaFrecuente, CarritoItem,
                  Producto.opciones.through, PrecioCombinacion.opciones.through}


def _otra_cosa_se_perderia(producto):
    """Red de seguridad, aparte de historial(): lo que Django borraria o dejaria
    sin producto al borrar, fuera de lo previsto. Devuelve su nombre o None.

    historial() mira los modelos que existen hoy. Si mañana se agrega otro que
    apunte a Producto (una reseña, otro tipo de pedido), este control lo ve
    solo y el producto se archiva en vez de borrarse. Un PROTECT levanta
    ProtectedError aca, antes de borrar nada.
    """
    recolector = Collector(using=producto._state.db or "default")
    recolector.collect([producto])
    for modelo, objetos in recolector.data.items():
        if objetos and modelo not in _SE_VAN_CON_EL:
            return str(modelo._meta.verbose_name_plural)
    for consulta in recolector.fast_deletes:
        if consulta.model not in _SE_VAN_CON_EL and consulta.exists():
            return str(consulta.model._meta.verbose_name_plural)
    for (campo, _valor), grupos in recolector.field_updates.items():
        for objetos in grupos:
            if objetos.exists() if hasattr(objetos, "exists") else objetos:
                return str(campo.model._meta.verbose_name_plural)
    return None


class _NoSeBorra(Exception):
    """El producto tiene algo que borrarlo se llevaria: se archiva."""


def _borrar(producto, destino, usuario):
    """Borra un producto SIN historia y deja su direccion redirigiendo (301).

    En una transaccion y con el producto bloqueado: la historia se vuelve a
    revisar adentro, porque entre que se abrio la confirmacion y se apreto el
    boton pudo entrar un pedido.
    """
    with transaction.atomic():
        producto = Producto.objects.select_for_update().get(pk=producto.pk)
        if historial(producto):
            raise _NoSeBorra
        # Las direcciones que ya llevaban a ESTE producto pasan a su destino
        # nuevo: sin cadenas de 301 ni flechas a una pagina que ya no existe.
        RedireccionProducto.objects.filter(destino=producto).update(destino=destino)
        if _otra_cosa_se_perderia(producto):
            raise _NoSeBorra
        if producto.slug:
            # Una fila vieja con la misma direccion (de un producto que la
            # tuvo antes) queda reemplazada por la de hoy.
            RedireccionProducto.objects.filter(slug=producto.slug).delete()
        RedireccionProducto.objects.create(slug=producto.slug or None, pk_antiguo=producto.pk,
                                           nombre=producto.nombre, destino=destino,
                                           borrado_por=(usuario or "")[:150])
        producto.delete()


def _archivar(request, producto, motivos):
    """Oculta el producto en vez de borrarlo y dice por que, en el aviso."""
    ya_estaba = not producto.visible
    if not ya_estaba:
        producto.visible = False
        producto.save(update_fields=["visible"])
    estado = "Ya estaba oculto y así sigue" if ya_estaba else "Quedó archivado"
    messages.warning(request, f"«{producto.nombre}» no se borró porque {_y(motivos)}: borrarlo se llevaría "
                              f"esa historia. {estado}: fuera del catálogo y de Google, con sus pedidos "
                              "completos. Lo puedes volver a mostrar cuando quieras.")
    return redirect("gestion:productos")


def producto_eliminar(request, pk):
    """Eliminar un producto. GET muestra lo que va a pasar; solo un POST
    confirmado hace algo, y la decision se vuelve a tomar al recibirlo (no se
    confia en lo que mostro la pagina).

    - Con historia (pedidos web, cajas o componentes del panel, costo): se
      ARCHIVA, nunca se borra.
    - Sin historia: se borra con sus fotos, precios y variantes, y su direccion
      queda con 301 al destino elegido (por defecto el catalogo).
    """
    producto = get_object_or_404(Producto, pk=pk, variante_de__isnull=True)
    motivos = historial(producto)
    destinos = list(Producto.objects.filter(visible=True, variante_de__isnull=True)
                    .exclude(pk=producto.pk).order_by("orden", "nombre"))
    elegido, error = "catalogo", ""

    if request.method == "POST" and request.POST.get("confirmar") == "si":
        if motivos:
            return _archivar(request, producto, motivos)
        elegido = request.POST.get("destino") or "catalogo"
        destino = next((d for d in destinos if str(d.pk) == elegido), None)
        if elegido != "catalogo" and destino is None:
            error = "Elige a dónde lleva la dirección antigua: el catálogo u otro producto que esté a la vista."
        else:
            nombre, url_antigua, se_van = producto.nombre, producto.get_absolute_url(), lo_que_se_va(producto)
            try:
                _borrar(producto, destino, request.user.get_username())
            except (_NoSeBorra, ProtectedError, RestrictedError, IntegrityError):
                # Nunca un 500: algo depende del producto, asi que se archiva.
                producto.refresh_from_db()
                return _archivar(request, producto, historial(producto) or ["hay datos que dependen de él"])
            junto = f", junto con {_y(se_van)}" if se_van else ""
            llega = f"«{destino.nombre}» ({destino.get_absolute_url()})" if destino else "el catálogo (/productos/)"
            messages.success(request, f"«{nombre}» eliminado{junto}. Quien entre a {url_antigua} llega a {llega}.")
            return redirect("gestion:productos")

    return render(request, "gestion/producto_eliminar.html", {
        "producto": producto,
        "motivos": motivos,
        "motivos_texto": _y(motivos) if motivos else "",
        "se_van_texto": "" if motivos else _y(["su foto principal", *lo_que_se_va(producto)]),
        "destinos": destinos,
        "elegido": elegido,
        "error": error,
    })
