"""Vẽ ảnh minh họa sản phẩm dạng SVG (thay cho ảnh có bản quyền).

Admin có thể thay bằng ảnh thật trong trang quản trị ở Giai đoạn 5.
"""


def shade(hex_color, p):
    """Làm sáng (p>0) hoặc tối (p<0) một màu theo phần trăm."""
    n = int(hex_color.lstrip("#"), 16)
    r, g, b = n >> 16, (n >> 8) & 255, n & 255
    f, t = (0 if p < 0 else 255), abs(p) / 100
    r, g, b = (round((f - c) * t + c) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def _camera(style, c2):
    return {
        "apple": f'<rect x="14" y="14" width="66" height="66" rx="18" fill="{c2}" opacity=".9"/>'
                 '<circle cx="34" cy="34" r="13" fill="#1d1d1f"/><circle cx="34" cy="62" r="13" fill="#1d1d1f"/>'
                 '<circle cx="60" cy="48" r="13" fill="#1d1d1f"/><circle cx="34" cy="34" r="5" fill="#3a4a7a"/>'
                 '<circle cx="34" cy="62" r="5" fill="#3a4a7a"/><circle cx="60" cy="48" r="5" fill="#3a4a7a"/>',
        "apple2": f'<rect x="14" y="14" width="44" height="66" rx="16" fill="{c2}" opacity=".9"/>'
                  '<circle cx="36" cy="34" r="12" fill="#1d1d1f"/><circle cx="36" cy="62" r="12" fill="#1d1d1f"/>'
                  '<circle cx="36" cy="34" r="4.5" fill="#3a4a7a"/><circle cx="36" cy="62" r="4.5" fill="#3a4a7a"/>',
        "apple1": f'<rect x="14" y="14" width="44" height="44" rx="14" fill="{c2}" opacity=".9"/>'
                  '<circle cx="36" cy="36" r="12" fill="#1d1d1f"/><circle cx="36" cy="36" r="4.5" fill="#3a4a7a"/>',
        "applebar": f'<rect x="4" y="16" width="146" height="44" rx="22" fill="{c2}" opacity=".9"/>'
                    '<circle cx="30" cy="38" r="12" fill="#1d1d1f"/><circle cx="30" cy="38" r="4.5" fill="#3a4a7a"/>',
        "samsung": "".join(f'<circle cx="30" cy="{y}" r="12" fill="#111" stroke="{c2}" stroke-width="3"/>' for y in (30, 60, 90))
                   + '<circle cx="56" cy="34" r="5" fill="#333"/>',
        "samsung2": "".join(f'<circle cx="30" cy="{y}" r="11" fill="#111" stroke="{c2}" stroke-width="3"/>' for y in (30, 58)),
        "flip": f'<rect x="10" y="10" width="134" height="110" rx="20" fill="#111"/><circle cx="34" cy="36" r="11" fill="#222" stroke="{c2}" stroke-width="3"/>'
                f'<circle cx="34" cy="68" r="11" fill="#222" stroke="{c2}" stroke-width="3"/><rect x="58" y="22" width="76" height="86" rx="12" fill="#0b1020"/>',
        "xiaomi": f'<rect x="16" y="16" width="62" height="62" rx="16" fill="{c2}"/><circle cx="36" cy="36" r="11" fill="#1a1a1a"/>'
                  '<circle cx="60" cy="36" r="11" fill="#1a1a1a"/><circle cx="36" cy="60" r="11" fill="#1a1a1a"/><circle cx="60" cy="60" r="5" fill="#eee"/>',
        "oppo": f'<rect x="16" y="16" width="44" height="80" rx="22" fill="{c2}"/><circle cx="38" cy="38" r="12" fill="#151515"/><circle cx="38" cy="72" r="12" fill="#151515"/>',
        "vivo": f'<circle cx="50" cy="50" r="34" fill="{c2}"/><circle cx="38" cy="40" r="11" fill="#141414"/>'
                '<circle cx="62" cy="40" r="11" fill="#141414"/><circle cx="50" cy="63" r="11" fill="#141414"/>',
        "round": f'<circle cx="77" cy="56" r="44" fill="{c2}"/><circle cx="60" cy="44" r="13" fill="#141414"/>'
                 '<circle cx="94" cy="44" r="13" fill="#141414"/><circle cx="60" cy="74" r="13" fill="#141414"/><circle cx="94" cy="74" r="6" fill="#eee"/>',
    }.get(style, "")


def phone_svg(style, c1, label=""):
    c2 = shade(c1, 22)
    gid = "g" + c1.lstrip("#")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-20 -6 210 360" role="img" aria-label="{label}">
<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{shade(c1, -18)}"/></linearGradient></defs>
<rect x="3" y="3" width="164" height="342" rx="30" fill="{shade(c1, -30)}"/>
<rect x="7" y="7" width="156" height="334" rx="27" fill="url(#{gid})"/>
<rect x="12" y="30" width="20" height="290" rx="10" fill="#fff" opacity=".08"/>
<g transform="translate(8,8)">{_camera(style, c2)}</g>
</svg>'''


def accessory_svg(kind, c, label=""):
    s = {
        "op-lung": f'<rect x="50" y="18" width="100" height="164" rx="20" fill="{c}"/><rect x="58" y="26" width="84" height="148" rx="14" fill="{shade(c, 25)}"/><rect x="62" y="30" width="40" height="40" rx="12" fill="{shade(c, -25)}"/>',
        "kinh-cuong-luc": '<rect x="52" y="16" width="96" height="168" rx="18" fill="#DCEBFA" stroke="#9BC3EC" stroke-width="3"/><path d="M70 40l50 0-60 110z" fill="#fff" opacity=".7"/><rect x="88" y="24" width="24" height="5" rx="2.5" fill="#9BC3EC"/>',
        "sac": f'<rect x="62" y="56" width="76" height="80" rx="18" fill="{c}" stroke="#d1d5db" stroke-width="2"/><rect x="80" y="30" width="10" height="28" rx="3" fill="#9aa3b2"/><rect x="110" y="30" width="10" height="28" rx="3" fill="#9aa3b2"/><path d="M104 74l-14 22h12l-6 20 18-26h-12l6-16z" fill="{shade(c, -60) if c.upper() in ("#F3F4F6", "#FFFFFF") else "#fff"}"/>',
        "cap": f'<path d="M60 40c60 0 80 30 40 60s-30 70 40 70" stroke="{c}" stroke-width="9" fill="none" stroke-linecap="round"/><rect x="40" y="28" width="30" height="24" rx="6" fill="#9aa3b2"/><rect x="132" y="158" width="30" height="24" rx="6" fill="#9aa3b2"/>',
        "tai-nghe": f'<rect x="38" y="80" width="124" height="80" rx="38" fill="#F3F4F6" stroke="#D1D5DB" stroke-width="3"/><path d="M40 112h120" stroke="#D1D5DB" stroke-width="3"/><circle cx="100" cy="134" r="4" fill="{c}"/>'
                    f'<g transform="translate(64 30)"><rect width="26" height="52" rx="13" fill="#fff" stroke="#D1D5DB" stroke-width="3"/><circle cx="13" cy="14" r="6" fill="{c}"/></g>'
                    f'<g transform="translate(110 30)"><rect width="26" height="52" rx="13" fill="#fff" stroke="#D1D5DB" stroke-width="3"/><circle cx="13" cy="14" r="6" fill="{c}"/></g>',
        "tai-nghe-chup": f'<path d="M50 120V96a50 50 0 0 1 100 0v24" stroke="{c}" stroke-width="12" fill="none" stroke-linecap="round"/><rect x="34" y="108" width="36" height="62" rx="16" fill="{c}"/><rect x="130" y="108" width="36" height="62" rx="16" fill="{c}"/>',
        "sac-du-phong": f'<rect x="58" y="22" width="84" height="156" rx="16" fill="{c}"/><rect x="72" y="38" width="56" height="10" rx="5" fill="{shade(c, 30)}"/>'
                        '<g fill="#7CFFB2"><rect x="72" y="150" width="10" height="6" rx="2"/><rect x="86" y="150" width="10" height="6" rx="2"/><rect x="100" y="150" width="10" height="6" rx="2"/><rect x="114" y="150" width="10" height="6" rx="2" opacity=".35"/></g>',
        "dong-ho": f'<rect x="78" y="10" width="44" height="40" rx="8" fill="{shade(c, -20)}"/><rect x="78" y="150" width="44" height="40" rx="8" fill="{shade(c, -20)}"/>'
                   '<rect x="58" y="44" width="84" height="112" rx="26" fill="#1f2937"/><rect x="66" y="52" width="68" height="96" rx="20" fill="#0b1020"/>'
                   f'<path d="M78 104h12l4-10 7 18 5-8h16" stroke="{c}" stroke-width="3.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
        "dong-ho-tron": f'<rect x="80" y="8" width="40" height="44" rx="8" fill="{shade(c, -20)}"/><rect x="80" y="148" width="40" height="44" rx="8" fill="{shade(c, -20)}"/>'
                        '<circle cx="100" cy="100" r="56" fill="#1f2937"/><circle cx="100" cy="100" r="47" fill="#0b1020"/>'
                        f'<path d="M100 70v32l18 12" stroke="{c}" stroke-width="4" fill="none" stroke-linecap="round"/>',
    }[kind]
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" role="img" aria-label="{label}">{s}</svg>'


def post_cover_svg(bg, style, c1):
    inner = phone_svg(style, c1)
    inner = inner.replace('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-20 -6 210 360"', '<svg x="250" y="20" width="140" height="240" viewBox="-20 -6 210 360"')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360"><rect width="640" height="360" fill="{bg}"/>{inner}</svg>'
