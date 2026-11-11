/* Trang chủ: banner, đếm ngược, lọc phụ kiện, so sánh, chọn máy */
(function () {
  const VND = n => Number(n).toLocaleString('vi-VN') + '₫';
  const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  /* Banner tự chuyển sau 5 giây */
  const slides = [...document.querySelectorAll('.slide')], dots = document.querySelector('.dots');
  if (slides.length) {
    let i = 0, t;
    slides.forEach((_, k) => { const b = document.createElement('button'); b.type = 'button'; b.setAttribute('aria-label', 'Banner ' + (k + 1)); b.onclick = () => { go(k); restart(); }; dots.appendChild(b); });
    function go(k) { slides[i].classList.remove('on'); dots.children[i].classList.remove('on'); i = k; slides[i].classList.add('on'); dots.children[i].classList.add('on'); }
    function restart() { clearInterval(t); if (slides.length > 1) t = setInterval(() => go((i + 1) % slides.length), 5000); }
    go(0); restart();
  }

  /* Đếm ngược tới lúc kết thúc giá sốc */
  /* Máy chủ gửi số giây còn lại (data-left) nên không lệch dù máy người xem ở múi giờ khác */
  const timer = document.querySelector('.timer[data-left]');
  if (timer) {
    const left0 = parseInt(timer.dataset.left, 10) || 0;
    const end = Date.now() + left0 * 1000;
    const f = v => String(v).padStart(2, '0');
    const tick = () => {
      let s = Math.max(0, Math.floor((end - Date.now()) / 1000));
      document.getElementById('hh').textContent = f(Math.floor(s / 3600));
      document.getElementById('mm').textContent = f(Math.floor(s % 3600 / 60));
      document.getElementById('ss').textContent = f(s % 60);
      if (s === 0 && left0 > 0 && !tick.done) { tick.done = true; setTimeout(() => location.reload(), 1500); }   // tải lại 1 lần để sang đợt mới
    };
    tick(); setInterval(tick, 1000);
  }

  /* Lọc phụ kiện theo loại (hiện tối đa 5) */
  const chips = document.getElementById('accChips');
  if (chips) {
    const items = [...document.querySelectorAll('#accGrid .acc-item')];
    const show = k => { let n = 0; items.forEach(it => { const ok = (k === 'all' || it.dataset.k === k) && n < 5; if (ok) n++; it.style.display = ok ? 'contents' : 'none'; }); };
    chips.addEventListener('click', e => { const b = e.target.closest('.chip'); if (!b) return; chips.querySelectorAll('.chip').forEach(c => c.classList.toggle('on', c === b)); show(b.dataset.k); });
    show('all');
  }

  /* Chọn máy theo nhu cầu: 3 câu hỏi, chấm điểm trên dữ liệu thật */
  const quiz = document.getElementById('quiz');
  if (quiz && window.FINDER) {
    const QS = [
      { h: 'Ngân sách của bạn khoảng bao nhiêu?', o: [['Dưới 5 triệu', [0, 5e6]], ['5 – 10 triệu', [5e6, 10e6]], ['10 – 20 triệu', [10e6, 20e6]], ['Trên 20 triệu', [20e6, 1e12]]] },
      { h: 'Bạn dùng điện thoại nhiều nhất để làm gì?', o: [['Chụp ảnh, quay video', 'cam'], ['Chơi game', 'game'], ['Cần pin trâu', 'pin'], ['Máy mỏng nhẹ', 'slim']] },
      { h: 'Bạn thích hệ điều hành nào?', o: [['iPhone (iOS)', 'ios'], ['Android', 'android'], ['Sao cũng được', 'any']] }
    ];
    let step = 0, ans = [];
    const render = () => {
      if (step < QS.length) {
        const s = QS[step];
        quiz.innerHTML = `<div class="q-step">Câu ${step + 1}/3</div><h3>${s.h}</h3><div class="opts">${s.o.map((o, k) => `<button type="button" data-k="${k}">${o[0]}</button>`).join('')}</div>
          <div class="progress">${QS.map((_, k) => `<i class="${k <= step ? 'on' : ''}"></i>`).join('')}</div>`;
        quiz.querySelectorAll('.opts button').forEach(b => b.onclick = () => { ans.push(s.o[+b.dataset.k][1]); step++; render(); });
        return;
      }
      const [[lo, hi], need, os] = ans;
      const bkey = ['duoi-5', '5-10', '10-20', 'tren-20'][[0, 5e6, 10e6, 20e6].indexOf(lo)];
      const why = `/chon-may?ngan-sach=${bkey}&nhu-cau=${need}&he-dieu-hanh=${os}#ket-qua`;
      const mid = (lo + Math.min(hi, 4e7)) / 2;
      const list = window.FINDER.filter(p => p.in_stock && (os === 'any' || (os === 'ios' ? p.brand === 'apple' : p.brand !== 'apple')))
        .map(p => {
          let score = 0;
          if (p.price >= lo && p.price < hi) score += 100; else score -= Math.abs(p.price - mid) / 1e6 * 4;
          if (p.needs.split(',').includes(need)) score += 40;
          return { p, score };
        })
        .sort((a, b) => b.score - a.score).slice(0, 3).map(x => x.p);
      quiz.innerHTML = `<div class="q-step">Gợi ý cho bạn</div><h3>${list.length ? '3 máy phù hợp nhất' : 'Chưa có máy phù hợp'}</h3>
        <div class="result">${list.map(p => `<a href="${p.url}"><img src="${p.image}" alt=""><span><span class="n">${esc(p.name)}</span><br><span class="p num">${VND(p.price)}</span></span></a>`).join('')}</div>
        <div style="display:flex;justify-content:space-between;margin-top:10px"><button type="button" class="again" style="margin:0">Làm lại</button><a href="${why}" style="font-size:14px;font-weight:600;color:var(--primary)">Xem vì sao hợp</a></div>`;
      quiz.querySelector('.again').onclick = () => { step = 0; ans = []; render(); };
    };
    render();
  }
})();
