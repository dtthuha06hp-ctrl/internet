/* Danh mục: lọc và sắp xếp không tải lại cả trang, URL luôn khớp bộ lọc */
(function () {
  const root = () => document.getElementById('catalog');

  async function go(url, push = true) {
    const r = root();
    r.classList.add('loading');
    try {
      const res = await fetch(url, { headers: { 'X-Partial': '1' } });
      const html = await res.text();
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const fresh = doc.getElementById('catalog');
      if (!fresh) { location.href = url; return; }
      const wasOpen = document.body.classList.contains('filters-open');
      r.replaceWith(fresh);
      document.title = doc.title;
      if (push) history.pushState({ url }, '', url);
      if (wasOpen) document.body.classList.add('filters-open');
      renderCmp();
    } catch (e) { location.href = url; }
  }

  function formUrl(extra) {
    const form = document.getElementById('filterForm');
    const base = root().dataset.base;
    const params = new URLSearchParams();
    const multi = {};
    for (const [k, v] of new FormData(form)) {
      if (!v) continue;
      (multi[k] = multi[k] || []).push(v);
    }
    Object.assign(multi, extra || {});
    for (const k in multi) if (multi[k] && multi[k].length) params.set(k, [].concat(multi[k]).join(','));
    if (params.get('sap-xep') === 'noi-bat') params.delete('sap-xep');
    const s = params.toString().replace(/%2C/g, ',');
    return base + (s ? '?' + s : '');
  }

  document.addEventListener('change', e => {
    if (e.target.closest('#filterForm') && e.target.type !== 'number') go(formUrl());
    if (e.target.id === 'sortSel') go(formUrl({ 'sap-xep': [e.target.value] }));
  });
  document.addEventListener('submit', e => {
    if (e.target.id === 'filterForm') { e.preventDefault(); go(formUrl()); }
  });
  document.addEventListener('click', e => {
    const a = e.target.closest('a[data-nav]');
    if (a) { e.preventDefault(); go(a.href); return; }
    const q = e.target.closest('[data-quick]');
    if (q) {
      const form = document.getElementById('filterForm');
      const box = form.querySelector(`input[name="${q.dataset.quick}"][value="${q.dataset.val}"]`);
      if (box) { box.checked = !box.checked; go(formUrl()); }
      else go(root().dataset.base + '?' + q.dataset.quick + '=' + q.dataset.val);
      return;
    }
    const more = e.target.closest('a[data-more]');
    if (more) {
      e.preventDefault();
      more.textContent = 'Đang tải…';
      const y = window.scrollY;
      go(more.href).then(() => window.scrollTo(0, y));
      return;
    }
    if (e.target.closest('[data-open-filters]')) document.body.classList.add('filters-open');
    if (e.target.closest('[data-close-filters]')) document.body.classList.remove('filters-open');
  });
  window.addEventListener('popstate', () => go(location.href, false));
})();
