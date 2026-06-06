# Dulcecitaa - Checklist de publicacion y operacion

## Requisitos previos
- Python 3.11+
- Entorno virtual activo
- Base de datos migrada
- Variables de entorno en `.env`

## Variables `.env` recomendadas (produccion)
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com`
- `BRAND_NAME=Dulcecitaa`
- `WEBSITE_URL=https://tu-dominio.com`
- `WHATSAPP_URL=https://wa.me/569XXXXXXXX`
- `SHIPPING_COST=2500`
- `PICKUP_POINT_LABEL=Retiro coordinado por WhatsApp`
- `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
- `EMAIL_HOST=smtp.gmail.com`
- `EMAIL_PORT=587`
- `EMAIL_USE_TLS=True`
- `EMAIL_HOST_USER=correo@tudominio.com`
- `EMAIL_HOST_PASSWORD=app_password_o_credencial`
- `DEFAULT_FROM_EMAIL=ventas@tudominio.com`
- `CONTACT_EMAIL=ventas@tudominio.com`

## Pasos tecnicos antes de publicar
1. Instalar dependencias:
   - `pip install -r requirements.txt`
2. Ejecutar migraciones:
   - `python manage.py migrate`
3. Recolectar estaticos:
   - `python manage.py collectstatic --noinput`
4. Verificar configuracion:
   - `python manage.py check`
5. Crear superusuario (si falta):
   - `python manage.py createsuperuser`

## Validacion funcional minima
1. Catalogo:
   - Buscar por nombre.
   - Filtrar por categoria.
   - Filtrar solo destacados.
2. Carrito:
   - Agregar/quitar items.
   - Verificar total.
3. Checkout:
   - Probar retiro y despacho.
   - Confirmar calculo de despacho en total.
   - Confirmar comuna/sector.
4. Exito de compra:
   - Verificar resumen final.
   - Verificar enlace WhatsApp prellenado.
5. Correos:
   - Contacto y corporativo.
   - Pedido cliente y pedido negocio.

## Checklist responsive
- Home: hero, bloques comerciales, FAQ.
- Catalogo: barra de filtros y tarjetas.
- Checkout: formulario y resumen lateral.
- Exito: resumen + CTA WhatsApp.
- Navbar y footer en movil.

## Checklist SEO minimo
- `title` por pagina.
- `meta description` por pagina.
- OpenGraph basico en `base.html`.
- Favicon cargado.
- Texto alternativo en imagenes de producto.

## Deploy (Render/Railway/VPS)
1. Configurar variables de entorno en el panel del proveedor.
2. Ejecutar:
   - `python manage.py migrate`
   - `python manage.py collectstatic --noinput`
3. Levantar app con WSGI:
   - `reposteria.wsgi:application`
4. Probar dominio con `DEBUG=False`.

## Comandos de prueba automatica
- `python manage.py test`
- `python manage.py check`
