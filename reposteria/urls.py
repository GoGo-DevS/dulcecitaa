from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as media_serve

from BebesitaAPP import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('panel/', include('gestion.urls')),
    path('', views.home, name='home'),
    path('productos/', views.productos, name='productos'),
    path('corporativo/', views.corporativo, name='corporativo'),
    path('contacto/', views.contacto, name='contacto'),

    # Carrito (por sesion)
    path('carrito/', views.mostrar_carrito, name='carrito'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/quitar/<int:producto_id>/', views.quitar_carrito, name='quitar_carrito'),
    path('carrito/agregar/<int:producto_id>/ajax/', views.agregar_carrito_ajax, name='agregar_carrito_ajax'),
    path('carrito/json/', views.carrito_json, name='carrito_json'),
    path('carrito/eliminar/<int:producto_id>/ajax/', views.eliminar_carrito_ajax, name='eliminar_carrito_ajax'),
    path('carrito/decrementar/<int:producto_id>/ajax/', views.decrementar_carrito_ajax, name='decrementar_carrito_ajax'),

    path('producto/<int:pk>/', views.producto_detalle, name='producto_detalle'),

    # Checkout
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/exito/<int:pedido_id>/', views.checkout_exito, name='checkout_exito'),
]

# Servir imágenes de /media/ también en producción (Render).
# Las fotos de productos van versionadas en el repo, así que es seguro servirlas.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", media_serve, {"document_root": settings.MEDIA_ROOT}),
]
