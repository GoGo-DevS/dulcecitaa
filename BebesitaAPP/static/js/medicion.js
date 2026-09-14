// Eventos que no dependen de una pagina en particular: cada toque en WhatsApp,
// Instagram o un boton de /links. Un solo escuchador en el documento, asi sirve
// tambien para enlaces que se agregan despues (modal de producto).
(function () {
  if (!window.dcMedir) return;

  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[href]');
    if (!a) return;
    var href = a.getAttribute('href') || '';
    var donde = window.location.pathname;

    var boton = href.match(/\/links\/ir\/([\w-]+)\/?/);
    if (boton) {
      window.dcMedir('links_click', { boton: boton[1] });
      if (boton[1] === 'whatsapp') window.dcMedir('click_whatsapp', { ubicacion: 'links' });
      return;
    }
    if (href.indexOf('wa.me') !== -1 || href.indexOf('whatsapp.com') !== -1) {
      window.dcMedir('click_whatsapp', { ubicacion: donde });
    } else if (href.indexOf('instagram.com') !== -1) {
      window.dcMedir('click_instagram', { ubicacion: donde });
    }
  });
})();
