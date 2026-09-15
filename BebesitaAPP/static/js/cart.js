(function () {
  // El minimo lo publica el servidor en el <body>: el respaldo del contador
  // no puede decir "1" cuando no se puede comprar menos de 10.
  const MINIMO = parseInt(document.body.dataset.minimo || '1', 10) || 1;
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return decodeURIComponent(parts.pop().split(';').shift());
  }

  const csrftoken = getCookie('csrftoken');
  const fmt = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });

  function showToast(msg) {
    const el = document.getElementById('toast-cart');
    const body = document.getElementById('toast-cart-body');
    if (!el || !body) return;
    body.textContent = msg || 'Producto agregado al carrito';
    const toast = new bootstrap.Toast(el);
    toast.show();
  }

  function pulseCartCount() {
    const badge = document.getElementById('cart-count');
    if (!badge) return;
    badge.classList.remove('is-bump');
    // restart animation
    void badge.offsetWidth;
    badge.classList.add('is-bump');
  }

  function setCartCount(n) {
    const badge = document.getElementById('cart-count');
    if (!badge) return;
    const current = Number.parseInt(badge.textContent || '0', 10);
    badge.textContent = n;
    const fab = document.getElementById('cart-fab');
    if (fab) fab.classList.toggle('is-empty', !Number(n));
    if (Number.isFinite(current) && current !== n) pulseCartCount();
  }

  function setCartTotal(value) {
    const totalEl = document.getElementById('cart-total');
    if (!totalEl || value == null) return;
    totalEl.textContent = fmt.format(value);
  }

  function switchToQty(productCtl, qty) {
    if (!productCtl) return;
    const addBtn = productCtl.querySelector('.btn-add-only');
    const pill = productCtl.querySelector('.qty-control');
    const qtyEl = productCtl.querySelector('.qty');
    if (qtyEl) qtyEl.textContent = qty != null ? qty : MINIMO;
    if (addBtn) addBtn.classList.add('d-none');
    if (pill) pill.classList.remove('d-none');
  }

  function switchToAdd(productCtl) {
    if (!productCtl) return;
    const addBtn = productCtl.querySelector('.btn-add-only');
    const pill = productCtl.querySelector('.qty-control');
    if (pill) pill.classList.add('d-none');
    if (addBtn) addBtn.classList.remove('d-none');
    const qtyEl = productCtl.querySelector('.qty');
    if (qtyEl) qtyEl.textContent = '0';
  }

  function flashButton(btn) {
    if (!btn) return;
    btn.classList.remove('is-success');
    void btn.offsetWidth;
    btn.classList.add('is-success');
    setTimeout(() => btn.classList.remove('is-success'), 520);
  }

  function setButtonBusy(btn, busy) {
    if (!btn) return;
    btn.disabled = busy;
    btn.classList.toggle('is-busy', busy);
  }

  // Lo ultimo que se sabe del carrito, por linea ("15-1": 10). Lo usa el
  // cambio de cobertura: al pasar de chocolate a blanco la tarjeta tiene que
  // mostrar cuantos de ESA cobertura hay, sin preguntarle otra vez al servidor.
  let cartCache = {};

  function claveDe(scope) {
    const ids = [...scope.querySelectorAll('[data-opciones] input:checked')]
      .map((i) => parseInt(i.value, 10))
      .sort((a, b) => a - b);
    return [scope.dataset.pid, ...ids].join('-');
  }

  function aplicarSeleccion(scope) {
    const clave = claveDe(scope);
    let recargo = 0;
    scope.querySelectorAll('[data-opciones]').forEach((grupo) => {
      const elegida = grupo.querySelector('input:checked');
      const nombre = grupo.querySelector('[data-opcion-nombre]');
      if (elegida && nombre) nombre.textContent = elegida.dataset.nombre;
      if (elegida) recargo += parseInt(elegida.dataset.recargo || '0', 10);
    });
    // Precio fijo por combinacion (tortas) si existe; si no, base + recargos.
    let fijos = {};
    try { fijos = JSON.parse(scope.dataset.precios || '{}'); } catch (e) { fijos = {}; }
    const claveOpciones = clave.split('-').slice(1).join('-');
    scope.querySelectorAll('[data-precio]').forEach((el) => {
      const precio = claveOpciones in fijos ? fijos[claveOpciones] : parseInt(el.dataset.precio, 10) + recargo;
      el.textContent = '$' + precio;
    });
    scope.querySelectorAll('.product-ctl').forEach((ctl) => {
      ctl.setAttribute('data-id', clave);
      const qty = cartCache[clave] || 0;
      if (qty > 0) switchToQty(ctl, qty);
      else switchToAdd(ctl);
    });
    const link = scope.querySelector('[data-agregar-ver]');
    if (link) link.setAttribute('href', `/carrito/agregar/${clave}/`);
  }

  // Nota de la linea (torta): se guarda sola 600 ms despues de dejar de escribir.
  let notaTimer = null;
  document.addEventListener('input', (e) => {
    const campo = e.target.closest('[data-nota-linea]');
    if (!campo) return;
    const estado = campo.parentElement.querySelector('[data-nota-estado]');
    clearTimeout(notaTimer);
    if (estado) estado.textContent = '';
    notaTimer = setTimeout(async () => {
      try {
        const body = new URLSearchParams({ nota: campo.value });
        const resp = await fetch(`/carrito/nota/${campo.dataset.notaLinea}/`, {
          method: 'POST', body,
          headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrftoken }
        });
        if (estado) estado.textContent = resp.ok ? 'Guardado' : 'No se pudo guardar';
      } catch (err) {
        if (estado) estado.textContent = 'No se pudo guardar';
      }
    }, 600);
  });

  document.addEventListener('change', (e) => {
    const input = e.target.closest('[data-opciones] input');
    const scope = input && input.closest('[data-linea-scope]');
    if (scope) aplicarSeleccion(scope);
  });

  function actualizarBox(row, box, pid, data) {
    // Si la linea salio (bajo el minimo) o la caja quedo vacia, se recarga:
    // cambian los numeros de las cajas y es mas simple que rearmar el bloque.
    if (data.recargar) { window.location.reload(); return; }
    setCartCount(data.cart_count || 0);
    const qtyEl = row.querySelector('.qty');
    if (qtyEl) qtyEl.textContent = data.qty;
    const sub = document.querySelector(`.line-subtotal[data-id="${pid}"][data-box="${box}"]`);
    if (sub) sub.textContent = fmt.format(data.item_subtotal || 0);
    const totalBox = document.querySelector(`[data-box-total="${box}"]`);
    if (totalBox) totalBox.textContent = fmt.format(data.box_total || 0);
    setCartTotal(data.total);
  }

  async function initQuantities() {
    try {
      const resp = await fetch('/carrito/json/');
      const data = await resp.json();
      if (!data || !data.ok) return;

      setCartCount(data.cart_count || 0);
      const cart = data.cart || {};
      cartCache = cart;

      document.querySelectorAll('.product-ctl').forEach((ctl) => {
        const pid = ctl.getAttribute('data-id');
        const qty = cart[pid] || 0;
        if (qty > 0) switchToQty(ctl, qty);
        else switchToAdd(ctl);
      });
    } catch {
      // no-op
    }
  }

  document.addEventListener('click', async (e) => {
    const plus = e.target.closest('.btn-plus');
    const minus = e.target.closest('.btn-minus');
    const trash = e.target.closest('.btn-trash');
    const addOnly = e.target.closest('.btn-add-only');
    const btnView = e.target.closest('.btn-view');

    if (btnView) {
      const id = btnView.getAttribute('data-id');
      try {
        setButtonBusy(btnView, true);
        const resp = await fetch(`/producto/${id}/?modal=1`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        const html = await resp.text();
        const body = document.getElementById('modal-producto-body');
        body.innerHTML = html;
        const modal = new bootstrap.Modal(document.getElementById('modalProducto'));
        modal.show();
        // En el catalogo la ficha se abre en este modal, no como pagina: aqui
        // es donde el cliente "ve el producto" para Analytics.
        if (window.dcMedir) {
          const nombre = body.querySelector('h1, h2');
          const precio = body.querySelector('[data-precio]');
          window.dcMedir('view_item', { currency: 'CLP', value: precio ? parseInt(precio.dataset.precio, 10) : undefined,
            items: [{ item_id: id, item_name: nombre ? nombre.textContent.trim() : '' }] });
        }
        setTimeout(initQuantities, 10);
      } catch {
        showToast('No se pudo cargar el producto.');
      } finally {
        setButtonBusy(btnView, false);
      }
      return;
    }

    if (addOnly) {
      const ctl = addOnly.closest('.product-ctl');
      // data-id ya trae la cobertura elegida ("15-2"): la pone aplicarSeleccion.
      const pid = ctl.getAttribute('data-id');
      try {
        setButtonBusy(addOnly, true);
        const resp = await fetch(`/carrito/agregar/${pid}/ajax/`, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrftoken }
        });
        const data = await resp.json();
        if (data && data.ok) {
          if (window.dcMedir) window.dcMedir('add_to_cart', { currency: 'CLP', items: [{ item_id: data.linea || pid, quantity: data.qty || MINIMO }] });
          cartCache[data.linea || pid] = data.qty || MINIMO;
          setCartCount(data.cart_count || 0);
          switchToQty(ctl, data.qty || MINIMO);
          flashButton(addOnly);
          showToast('Agregado al carrito');
        } else {
          showToast('No se pudo agregar.');
        }
      } catch {
        showToast('Error de red.');
      } finally {
        setButtonBusy(addOnly, false);
      }
      return;
    }

    if (plus) {
      const row = plus.closest('[data-id]') || plus.closest('.qty-control');
      const pid = row.getAttribute('data-id');
      const qtyEl = row.querySelector('.qty');

      try {
        setButtonBusy(plus, true);
        // Una linea de box va a su propia ruta: su minimo es otro y suma a su caja.
        const box = row.getAttribute('data-box');
        const url = box !== null ? `/carrito/box/${box}/sumar/${pid}/` : `/carrito/agregar/${pid}/ajax/`;
        const resp = await fetch(url, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrftoken }
        });
        const data = await resp.json();
        if (data && data.ok && box !== null) {
          actualizarBox(row, box, pid, data);
          flashButton(plus);
        } else if (data && data.ok) {
          cartCache[pid] = data.qty || 0;
          setCartCount(data.cart_count || 0);
          if (qtyEl) qtyEl.textContent = data.qty ?? (parseInt(qtyEl.textContent || '0', 10) + 1);

          const subEl = document.querySelector(`.line-subtotal[data-id="${pid}"]`);
          if (subEl && data.item_subtotal != null) subEl.textContent = fmt.format(data.item_subtotal);
          setCartTotal(data.total);
          flashButton(plus);
          showToast('Agregado al carrito');
        } else {
          showToast('No se pudo agregar.');
        }
      } catch {
        showToast('Error de red.');
      } finally {
        setButtonBusy(plus, false);
      }
      return;
    }

    if (minus) {
      const row = minus.closest('[data-id]') || minus.closest('.qty-control');
      const pid = row.getAttribute('data-id');
      const qtyEl = row.querySelector('.qty');

      try {
        setButtonBusy(minus, true);
        const box = row.getAttribute('data-box');
        const url = box !== null ? `/carrito/box/${box}/restar/${pid}/` : `/carrito/decrementar/${pid}/ajax/`;
        const resp = await fetch(url, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrftoken }
        });
        const data = await resp.json();
        if (data && data.ok && box !== null) {
          actualizarBox(row, box, pid, data);
          flashButton(minus);
        } else if (data && data.ok) {
          cartCache[pid] = data.qty || 0;
          setCartCount(data.cart_count || 0);
          if (qtyEl) qtyEl.textContent = data.qty || 0;

          const subEl = document.querySelector(`.line-subtotal[data-id="${pid}"]`);
          if (subEl) subEl.textContent = data.qty ? fmt.format(data.item_subtotal || 0) : fmt.format(0);
          setCartTotal(data.total);
          flashButton(minus);
          showToast(data.qty ? 'Se resto 1 unidad' : 'Producto eliminado del carrito');
        } else {
          showToast('No se pudo actualizar.');
        }
      } catch {
        showToast('Error de red.');
      } finally {
        setButtonBusy(minus, false);
      }
      return;
    }

    if (trash) {
      const row = trash.closest('[data-id]') || trash.closest('.product-ctl');
      const pid = row.getAttribute('data-id');
      const qtyEl = row.querySelector('.qty');

      try {
        setButtonBusy(trash, true);
        const resp = await fetch(`/carrito/eliminar/${pid}/ajax/`, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrftoken }
        });
        const data = await resp.json();
        if (data && data.ok) {
          delete cartCache[pid];
          setCartCount(data.cart_count || 0);
          if (qtyEl) qtyEl.textContent = '0';

          const productCtl = trash.closest('.product-ctl');
          if (productCtl) switchToAdd(productCtl);

          const subEl = document.querySelector(`.line-subtotal[data-id="${pid}"]`);
          if (subEl) subEl.textContent = fmt.format(0);
          setCartTotal(data.total);
          flashButton(trash);
          showToast('Producto eliminado del carrito');
        } else {
          showToast('No se pudo eliminar.');
        }
      } catch {
        showToast('Error de red.');
      } finally {
        setButtonBusy(trash, false);
      }
    }
  });

  if (document.querySelector('.product-ctl') || document.getElementById('cart-total')) {
    initQuantities();
  }
})();
