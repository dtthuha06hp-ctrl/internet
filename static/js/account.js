/* Trang tài khoản / đăng ký: hiện mật khẩu, bỏ yêu thích */
(function () {
  document.querySelectorAll('[data-toggle-pw]').forEach(b => b.addEventListener('click', () => {
    const i = document.getElementById(b.dataset.togglePw);
    const show = i.type === 'password';
    i.type = show ? 'text' : 'password';
    b.textContent = show ? 'Ẩn' : 'Hiện';
  }));
  document.addEventListener('click', async e => {
    const x = e.target.closest('[data-wish-id]');
    if (!x) return;
    const res = await toggleWish(+x.dataset.wishId);
    if (res && res.ok && !res.on) x.closest('.wish-wrap').remove();
  });
  const bad = document.querySelector('.field.bad input, .consent.bad input');
  if (bad) bad.focus();
})();
