(function () {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function initNavbarScroll() {
    const nav = document.querySelector('.site-navbar');
    if (!nav) return;

    const onScroll = () => {
      nav.classList.toggle('is-scrolled', window.scrollY > 12);
    };

    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  function initCatalogEnhancements() {
    const cards = document.querySelectorAll('[data-catalog-card]');
    if (!cards.length) return;

    cards.forEach((card, index) => {
      card.classList.add('reveal-item');
      card.style.setProperty('--reveal-delay', `${Math.min(index * 55, 330)}ms`);

      if (!reduceMotion) {
        card.addEventListener('mouseenter', () => card.classList.add('is-hovered'));
        card.addEventListener('mouseleave', () => card.classList.remove('is-hovered'));
      }
    });
  }

  function initReveal() {
    const selectors = [
      '.hero-premium .hero-copy',
      '.hero-premium .hero-media',
      '.hero-metrics li',
      '.page-hero',
      '.section-head',
      '.cta-band-inner',
      '.featured-card',
      '.surface-card',
      '.check-list li',
      '.split-grid > *',
      '.split-form-layout > *',
      '.product-detail-wrap',
      '.product-detail-media',
      '.product-detail-content',
      '.cart-item',
      '.cart-layout',
      '.cart-summary',
      '.checkout-layout',
      '.checkout-summary',
      '.checkout-form-card',
      '.split-form-copy',
      '.form-shell',
      '.success-card',
      '.empty-state',
      '.footer-grid > div',
      '.footer-legal',
      '.reveal-ready',
      '[data-reveal-item]',
      '.reveal-item',
      '.catalog-card',
      '.catalog-card.reveal-item'
    ];

    const elements = Array.from(new Set(Array.from(document.querySelectorAll(selectors.join(',')))));
    if (!elements.length) return;

    elements.forEach((el, idx) => {
      if (!el.classList.contains('reveal-item')) {
        el.classList.add('reveal-item');
        el.style.setProperty('--reveal-delay', `${Math.min(idx * 32, 260)}ms`);
      }
    });

    if (reduceMotion || !('IntersectionObserver' in window)) {
      elements.forEach((el) => el.classList.add('is-visible'));
      return;
    }

    const observer = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-visible');
          obs.unobserve(entry.target);
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -8% 0px' }
    );

    elements.forEach((el) => observer.observe(el));
  }

  function initRevealGroups() {
    const groups = document.querySelectorAll('[data-reveal-group]');
    if (!groups.length) return;

    groups.forEach((group) => {
      const items = group.querySelectorAll('[data-reveal-item]');
      items.forEach((item, idx) => {
        if (!item.classList.contains('reveal-item')) {
          item.classList.add('reveal-item');
        }
        if (!item.style.getPropertyValue('--reveal-delay')) {
          item.style.setProperty('--reveal-delay', `${Math.min(idx * 58, 340)}ms`);
        }
      });
    });
  }

  function initSmoothAnchors() {
    document.addEventListener('click', (event) => {
      const link = event.target.closest('a[href^="#"]');
      if (!link) return;

      const href = link.getAttribute('href');
      if (!href || href === '#') return;

      const target = document.querySelector(href);
      if (!target) return;

      event.preventDefault();
      target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
      if (target.tabIndex < 0) target.setAttribute('tabindex', '-1');
      target.focus({ preventScroll: true });
    });
  }

  function initFormsLoading() {
    document.querySelectorAll('form').forEach((form) => {
      form.addEventListener('submit', () => {
        const submit = form.querySelector('button[type="submit"], input[type="submit"]');
        if (!submit || submit.disabled) return;

        submit.dataset.originalText = submit.textContent;
        submit.disabled = true;
        submit.classList.add('is-loading');
        submit.textContent = 'Enviando...';
      });
    });
  }

  function initModalPolish() {
    const modalEl = document.getElementById('modalProducto');
    if (!modalEl) return;

    const focusableSelector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

    modalEl.addEventListener('shown.bs.modal', () => {
      document.body.classList.add('is-product-modal-open');
      const firstFocusable = modalEl.querySelector(focusableSelector);
      if (firstFocusable) firstFocusable.focus({ preventScroll: true });
    });

    modalEl.addEventListener('hidden.bs.modal', () => {
      document.body.classList.remove('is-product-modal-open');
    });
  }

  initNavbarScroll();
  initCatalogEnhancements();
  initRevealGroups();
  initReveal();
  initSmoothAnchors();
  initFormsLoading();
  initModalPolish();
})();
