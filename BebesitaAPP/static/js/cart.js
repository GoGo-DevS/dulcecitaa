(function () {
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
    if (qtyEl) qtyEl.textContent = qty != null ? qty : '1';
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

  async function initQuantities() {
    try {
      const resp = await fetch('/carrito/json/');
      const data = await resp.json();
      if (!data || !data.ok) return;

      setCartCount(data.cart_count || 0);
      const cart = data.cart || {};

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
      const pid = ctl.getAttribute('data-id');
      try {
        setButtonBusy(addOnly, true);
        const resp = await fetch(`/carrito/agregar/${pid}/ajax/`, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrftoken }
        });
        const data = await resp.json();
        if (data && data.ok) {
          setCartCount(data.cart_count || 0);
          switchToQty(ctl, data.qty || 1);
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
        const resp = await fetch(`/carrito/agregar/${pid}/ajax/`, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrftoken }
        });
        const data = await resp.json();
        if (data && data.ok) {
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
        const resp = await fetch(`/carrito/decrementar/${pid}/ajax/`, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrftoken }
        });
        const data = await resp.json();
        if (data && data.ok) {
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
