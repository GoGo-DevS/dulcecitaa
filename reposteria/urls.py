from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as media_serve

from django.contrib.sitemaps.views import sitemap

from BebesitaAPP import links as links_views
from BebesitaAPP import seo
from BebesitaAPP import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('panel/', include('gestion.urls')),
    path('', views.home, name='home'),

    # SEO tecnico
    path('robots.txt', seo.robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap, {'sitemaps': seo.SITEMAPS}, name='django.contrib.sitemaps.views.sitemap'),
    path('manifest.webmanifest', seo.manifest, name='manifest'),

    path('productos/', views.productos, name='productos'),
    path('corporativo/', views.corporativo, name='corporativo'),
    path('contacto/', views.contacto, name='contacto'),
    path('delivery/', views.delivery, name='delivery'),

    # Carrito (por sesion)
    path('carrito/', views.mostrar_carrito, name='carrito'),
    path('carrito/agregar/<str:linea>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/quitar/<str:linea>/', views.quitar_carrito, name='quitar_carrito'),
    path('carrito/agregar/<str:linea>/ajax/', views.agregar_carrito_ajax, name='agregar_carrito_ajax'),
    path('carrito/json/', views.carrito_json, name='carrito_json'),
    path('carrito/eliminar/<str:linea>/ajax/', views.eliminar_carrito_ajax, name='eliminar_carrito_ajax'),
    path('carrito/decrementar/<str:linea>/ajax/', views.decrementar_carrito_ajax, name='decrementar_carrito_ajax'),

    # Arma tu box
    path('arma-tu-box/', views.arma_tu_box, name='arma_tu_box'),
    path('carrito/box/<int:indice>/sumar/<str:linea>/', views.box_sumar_ajax, name='box_sumar_ajax'),
    path('carrito/box/<int:indice>/restar/<str:linea>/', views.box_restar_ajax, name='box_restar_ajax'),
    path('carrito/box/<int:indice>/quitar/', views.box_quitar, name='box_quitar'),

    # Pagina de la bio de Instagram y sus enlaces contados
    path('links/', links_views.links, name='links'),
    path('links/ir/<slug:slug>/', links_views.links_ir, name='links_ir'),

    path('producto/<int:pk>/', views.producto_detalle, name='producto_detalle'),
    path('productos/<slug:slug>/', views.producto_ficha, name='producto_ficha'),

    # Checkout
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/exito/<int:pedido_id>/', views.checkout_exito, name='checkout_exito'),
]

# Servir imágenes de /media/ también en producción (Render).
# Las fotos de productos van versionadas en el repo, así que es seguro servirlas.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", media_serve, {"document_root": settings.MEDIA_ROOT}),
]
