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

    # Pedidos
    path("pedidos/", views.pedidos_lista, name="pedidos"),
    path("pedidos/nuevo/", views.pedido_nuevo, name="pedido_nuevo"),
    path("pedidos/<int:pk>/", views.pedido_detalle, name="pedido_detalle"),
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
]
