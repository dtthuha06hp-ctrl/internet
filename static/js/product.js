/* Trang chi tiết: chọn dung lượng + màu -> đổi giá, ảnh, tồn kho, URL (không tải lại trang) */
(function () {
  const P = window.PRODUCT, VS = P.variants;
  const VND = n => Number(n).toLocaleString('vi-VN') + '₫';
  let cur = VS.find(v => v.sku === window.CURRENT_SKU) || VS[0];
  const $ = id => document.getElementById(id);

  function find(option, color) {
    return VS.find(v => v.option === option && v.color_name === color);
  }

  function render() {
    // nút dung lượng
    document.querySelectorAll('[data-option]').forEach(b => b.classList.toggle('on', b.dataset.option === cur.option));
    // nút màu: màu nào không có hoặc hết hàng ở dung lượng đang chọn thì làm mờ
    document.querySelectorAll('.swatch[data-color]').forEach(b => {
      const v = find(cur.option, b.dataset.color);
      b.classList.toggle('on', b.dataset.color === cur.color_name);
      b.classList.toggle('out', !v || v.available <= 0);
      b.disabled = !v || v.available <= 0;
      b.title = !v ? 'Không có màu này ở phiên bản đã chọn' : (v.available <= 0 ? b.dataset.color + ' – tạm hết hàng' : b.dataset.color);
    });
    document.querySelectorAll('.thumb').forEach(b => b.classList.toggle('on', b.dataset.color === cur.color_name));
    $('colorName').textContent = cur.color_name;
    $('mainImgEl').src = cur.image;
    $('mainImgEl').alt = P.name + ' màu ' + cur.color_name;
    $('priceEl').textContent = VND(cur.price);
    $('stickyPrice').textContent = VND(cur.price);
    $('pbLabel').textContent = cur.is_promo ? 'Giá sốc hôm nay' : 'Giá phải trả';
    const hasDisc = cur.list_price > cur.price;
    $('listEl').hidden = !hasDisc; $('listEl').textContent = VND(cur.list_price);
    $('saveEl').hidden = !hasDisc; $('saveEl').textContent = 'Tiết kiệm ' + VND(cur.list_price - cur.price);
    $('promoNote').hidden = !cur.is_promo;
    if (cur.is_promo) $('promoNote').textContent = '⚡ Còn ' + cur.promo_left + ' suất giá sốc hôm nay';
    const tag = $('tagSale');
    if (tag) { tag.hidden = cur.discount_pct < 5; tag.textContent = '−' + cur.discount_pct + '%'; }
    $('skuTxt').textContent = cur.sku;
    if ($('titleOpt')) $('titleOpt').textContent = cur.option;
    if ($('instEl')) $('instEl').textContent = VND(Math.round(cur.price / 12 / 1000) * 1000);
    const a = cur.available, st = $('stockEl');
    st.className = 'stock stock-' + (a <= 0 ? 'out' : a <= 5 ? 'low' : 'ok');
    st.textContent = a <= 0 ? 'Tạm hết hàng' : a <= 5 ? `Sắp hết – còn ${a} sản phẩm` : 'Còn hàng';
    document.querySelectorAll('[data-buy]').forEach(b => b.disabled = a <= 0);
    const main = document.querySelector('.btn-buy');
    main.querySelector('b').textContent = a <= 0 ? 'Tạm hết hàng' : 'Mua ngay';
    main.querySelector('small').textContent = a <= 0 ? 'Chọn phiên bản khác' : 'Giao tận nơi hoặc nhận tại cửa hàng';
    history.replaceState(null, '', P.url + '?sku=' + encodeURIComponent(cur.sku));
    document.title = P.name + ' ' + (cur.option || '') + ' – Nhịp Mobile';
  }

  document.addEventListener('click', e => {
    const o = e.target.closest('[data-option]');
    if (o) {
      // giữ màu đang chọn nếu còn hàng, nếu không chọn màu còn hàng đầu tiên
      const same = find(o.dataset.option, cur.color_name);
      cur = (same && same.available > 0) ? same
        : (VS.find(v => v.option === o.dataset.option && v.available > 0) || same || VS.find(v => v.option === o.dataset.option));
      render(); return;
    }
    const c = e.target.closest('.swatch[data-color], .thumb[data-color]');
    if (c) {
      const v = find(cur.option, c.dataset.color);
      if (v && (v.available > 0 || c.classList.contains('thumb'))) { cur = v; render(); }
      else if (c.classList.contains('thumb')) { $('mainImgEl').src = c.dataset.img; }
      return;
    }
    const cp = e.target.closest('[data-copy]');
    if (cp) {
      const code = cp.dataset.copy;
      (navigator.clipboard ? navigator.clipboard.writeText(code) : Promise.reject()).then(
        () => toast('Đã sao chép mã ' + code + '. Dán vào ô mã giảm giá ở giỏ hàng.', false),
        () => toast('Mã giảm giá: ' + code, false));
      cp.textContent = 'Đã sao chép';
      return;
    }
    const buy = e.target.closest('[data-buy]');
    if (buy && !buy.disabled) {
      buy.disabled = true;
      addToCart({ variant_id: cur.id, qty: 1 }, buy.dataset.buy === 'now' ? { go: '/thanh-toan' } : {})
        .finally(() => { buy.disabled = cur.available <= 0; });
      return;
    }
    const w = e.target.closest('[data-wish]');
    if (w) {
      toggleWish(P.id).then(d => { if (d && d.ok) { w.classList.toggle('on', d.on); w.textContent = d.on ? '♥' : '♡'; w.setAttribute('aria-pressed', d.on); } });
      return;
    }
    const tab = e.target.closest('[data-tab], [data-tab-link]');
    if (tab) {
      const id = tab.dataset.tab || tab.dataset.tabLink;
      document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.dataset.tab === id));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('on', p.id === id));
      if (tab.dataset.tabLink) { e.preventDefault(); document.querySelector('.tabs-wrap').scrollIntoView({ behavior: 'smooth' }); }
      return;
    }
    const s = e.target.closest('[data-star]');
    if (s) {
      const k = s.dataset.star;
      document.querySelectorAll('.rv-filter .chip').forEach(c => c.classList.toggle('on', c.dataset.star === k));
      document.querySelectorAll('.rv-list li').forEach(li => li.hidden = k !== 'all' && li.dataset.star !== k);
    }
  });

  // Thanh mua dính đáy: hiện khi đã cuộn qua khu nút mua
  const cta = $('ctaRow'), bar = $('stickyBuy');
  if (cta && bar && 'IntersectionObserver' in window) {
    new IntersectionObserver(([en]) => bar.classList.toggle('show', !en.isIntersecting && en.boundingClientRect.top < 0)).observe(cta);
  }
  render();
})();
