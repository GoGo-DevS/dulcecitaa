from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import GestionLoginForm

app_name = "gestion"

urlpatterns = [
    # Acceso
    path("login/", auth_views.LoginView.as_view(
        template_name="gestion/login.html",
        authentication_form=GestionLoginForm,
        redirect_authenticated_user=True,
    ), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="gestion:login"), name="logout"),

    path("", views.dashboard, name="dashboard"),

    # Clientes
    path("clientes/", views.clientes_lista, name="clientes"),
    path("clientes/nuevo/", views.cliente_nuevo, name="cliente_nuevo"),
    path("clientes/<int:pk>/editar/", views.cliente_editar, name="cliente_editar"),
    path("clientes/<int:pk>/eliminar/", views.cliente_eliminar, name="cliente_eliminar"),

    # Pedidos
    path("pedidos/", views.pedidos_lista, name="pedidos"),
    path("pedidos/nuevo/", views.pedido_nuevo, name="pedido_nuevo"),
    path("pedidos/<int:pk>/", views.pedido_detalle, name="pedido_detalle"),
    path("pedidos/<int:pk>/editar/", views.pedido_editar, name="pedido_editar"),
    path("pedidos/<int:pk>/nota/", views.pedido_nota, name="pedido_nota"),
    path("pedidos/<int:pk>/item/agregar/", views.pedido_item_agregar, name="pedido_item_agregar"),
    path("pedidos/<int:pk>/item/<int:item_pk>/eliminar/", views.pedido_item_eliminar, name="pedido_item_eliminar"),
    path("pedidos/<int:pk>/item/<int:item_pk>/componente/agregar/", views.componente_agregar, name="componente_agregar"),
    path("pedidos/<int:pk>/item/<int:item_pk>/componente/<int:comp_pk>/eliminar/", views.componente_eliminar, name="componente_eliminar"),
    path("pedidos/<int:pk>/estado/", views.pedido_estado, name="pedido_estado"),
    path("pedidos/<int:pk>/cliente/", views.pedido_cliente, name="pedido_cliente"),
    path("pedidos/<int:pk>/eliminar/", views.pedido_eliminar, name="pedido_eliminar"),

    # Compras
    path("pedidos/<int:pk>/compra/", views.compra_nueva, name="compra_nueva"),
    path("pedidos/<int:pk>/compra/<int:compra_pk>/eliminar/", views.compra_eliminar, name="compra_eliminar"),
    path("compra-granel/", views.compra_granel, name="compra_granel"),

    # Promociones: las campanas por fecha viven aca y no en /admin/
    path("promos/", views.promos, name="promos"),
    path("promos/nueva/", views.promo_form, name="promo_nueva"),
    path("promos/<int:pk>/editar/", views.promo_form, name="promo_editar"),
    path("promos/<int:pk>/encender/", views.promo_toggle, name="promo_toggle"),
    path("promos/<int:pk>/eliminar/", views.promo_eliminar, name="promo_eliminar"),

    # Costos por unidad
    path("costos/", views.costos, name="costos"),
    path("web/", views.web, name="web"),
]
