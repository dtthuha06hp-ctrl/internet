/* Dùng chung cho mọi trang người mua */
(function () {
  const VND = n => Number(n).toLocaleString('vi-VN') + '₫';
  const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  /* Thông báo nhỏ góc phải */
  let tt;
  window.toast = function (msg, link) {
    const t = document.getElementById('toast');
    if (!t) return;
    document.getElementById('toastTxt').textContent = msg;
    const a = document.getElementById('toastLink');
    a.style.display = link === false ? 'none' : '';
    t.classList.add('show');
    clearTimeout(tt);
    tt = setTimeout(() => t.classList.remove('show'), 2800);
  };

  /* Gợi ý tìm kiếm: gọi máy chủ sau khi gõ ≥ 2 ký tự */
  const q = document.getElementById('q'), box = document.getElementById('suggest');
  if (q && box) {
    let timer, active = -1;
    q.addEventListener('input', () => {
      clearTimeout(timer);
      const v = q.value.trim();
      if (v.length < 2) { box.classList.remove('show'); return; }
      timer = setTimeout(async () => {
        const res = await fetch('/api/goi-y?q=' + encodeURIComponent(v));
        const items = await res.json();
        active = -1;
        box.innerHTML = items.length
          ? items.map(x => `<a href="${x.url}"><img class="s-img" src="${x.image}" alt=""><span><span class="s-name">${esc(x.name)}</span><br><span class="s-price num">${VND(x.price)}</span></span></a>`).join('')
            + `<a href="/tim-kiem?q=${encodeURIComponent(v)}" style="justify-content:center;font-size:14px;color:var(--primary);font-weight:600">Xem tất cả kết quả</a>`
          : `<div class="empty">Không tìm thấy "${esc(v)}". Thử gõ tên hãng, ví dụ "samsung".</div>`;
        box.classList.add('show');
      }, 180);
    });
    q.addEventListener('keydown', e => {
      const links = [...box.querySelectorAll('a')];
      if (!box.classList.contains('show') || !links.length) return;
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        active = (active + (e.key === 'ArrowDown' ? 1 : -1) + links.length) % links.length;
        links.forEach((l, i) => l.classList.toggle('active', i === active));
      } else if (e.key === 'Enter' && active >= 0) {
        e.preventDefault(); location.href = links[active].href;
      } else if (e.key === 'Escape') box.classList.remove('show');
    });
    document.addEventListener('click', e => { if (!e.target.closest('.search')) box.classList.remove('show'); });
  }

  /* Menu tài khoản */
  const um = document.getElementById('userMenu');
  if (um) {
    const btn = um.querySelector('button');
    btn.addEventListener('click', e => { e.stopPropagation(); const o = um.classList.toggle('open'); btn.setAttribute('aria-expanded', o); });
    document.addEventListener('click', e => { if (!um.contains(e.target)) um.classList.remove('open'); });
  }

  /* So sánh: lưu tối đa 3 máy trong trình duyệt, dùng chung mọi trang */
  const KEY = 'nm_cmp';
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch (e) { return []; } };
  const save = l => { try { localStorage.setItem(KEY, JSON.stringify(l)); } catch (e) {} };
  window.cmpList = load;
  window.renderCmp = function () {
    const list = load(), bar = document.getElementById('cmpbar');
    document.querySelectorAll('.cmp[data-id]').forEach(b => {
      const on = list.some(x => x.id == b.dataset.id);
      b.classList.toggle('on', on);
      b.textContent = on ? '✓ Đã chọn' : (b.dataset.label || '＋ So sánh');
    });
    if (!bar) return;
    document.getElementById('slots').innerHTML = [0, 1, 2].map(k => `<div class="slot">${list[k] ? `<img src="${list[k].img}" alt="${esc(list[k].name || '')}" title="${esc(list[k].name || '')}">` : ''}</div>`).join('');
    document.getElementById('cmpTxt').textContent = `Đã chọn ${list.length}/3 máy`;
    document.getElementById('cmpGo').href = '/so-sanh?ids=' + list.map(x => x.id).join(',');
    bar.classList.toggle('show', list.length > 0);
  };
  document.addEventListener('click', e => {
    const c = e.target.closest('.cmp[data-id]');
    if (c) {
      let list = load();
      if (list.some(x => x.id == c.dataset.id)) list = list.filter(x => x.id != c.dataset.id);
      else {
        if (list.length >= 3) { toast('Chỉ so sánh tối đa 3 máy. Bỏ bớt một máy trên thanh so sánh.', false); return; }
        list.push({ id: +c.dataset.id, img: c.dataset.img, name: c.dataset.name });
      }
      save(list); renderCmp();
    }
    if (e.target.id === 'cmpClear') { save([]); renderCmp(); }
  });
  window.cmpSave = save;
  renderCmp();

  /* Thêm vào giỏ: gửi lên máy chủ, máy chủ tự kiểm tra tồn kho và giới hạn 3 cái */
  window.addToCart = async function (payload, opts) {
    opts = opts || {};
    try {
      const res = await fetch('/gio-hang/them', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(Object.assign({ csrf: window.NM.csrf }, payload))
      });
      const data = await res.json();
      const badge = document.getElementById('cartCount');
      if (badge) { badge.textContent = data.count; badge.classList.remove('bump'); void badge.offsetWidth; badge.classList.add('bump'); }
      if (opts.go && (data.ok || /tối đa/.test(data.message))) { location.href = opts.go; return data; }
      toast(data.message, data.ok);
      return data;
    } catch (e) { toast('Không kết nối được máy chủ. Hãy kiểm tra cửa sổ chạy web còn mở không.', false); }
  };
  /* Yêu thích: cần đăng nhập */
  window.toggleWish = async function (productId) {
    const res = await fetch('/yeu-thich/doi', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ csrf: window.NM.csrf, product_id: productId }) });
    const data = await res.json();
    if (data.login) {
      toast(data.message, false);
      setTimeout(() => location.href = '/dang-nhap?next=' + encodeURIComponent(location.pathname + location.search), 1200);
      return data;
    }
    toast(data.message, false);
    return data;
  };

  document.addEventListener('click', e => {
    const add = e.target.closest('.add[data-pid]');
    if (add) { add.disabled = true; addToCart({ product_id: +add.dataset.pid }).finally(() => add.disabled = false); }
  });
})();
