"""Bộ ghép giao diện: đọc file HTML trong templates/ và điền dữ liệu vào.

Cú pháp (giống Jinja/Django cho dễ học):
  {{ bien }}                    in ra giá trị (tự chống chèn mã độc)
  {{ gia|vnd }}                 dùng bộ lọc, ví dụ định dạng tiền
  {{ html|safe }}               in nguyên văn (chỉ dùng với nội dung tin cậy)
  {% if dieu_kien %} ... {% elif ... %} ... {% else %} ... {% endif %}
  {% for x in danh_sach %} ... {% endfor %}
  {% set x = bieu_thuc %}
  {% include "duong/dan.html" %}
  {% extends "layout/base.html" %}  +  {% block ten %} ... {% endblock %}
  {# ghi chú, không hiện ra #}
"""
import html
import os
import re
import config

_TOKEN = re.compile(r"({{.*?}}|{%.*?%}|{#.*?#})", re.S)
_BLOCK = re.compile(r"{%\s*block\s+(\w+)\s*%}(.*?){%\s*endblock\s*%}", re.S)
_EXTENDS = re.compile(r"^\s*{%\s*extends\s+[\"'](.+?)[\"']\s*%}")
_INCLUDE = re.compile(r"{%\s*include\s+[\"'](.+?)[\"']\s*%}")

_cache = {}


def _read(name):
    path = os.path.join(config.TEMPLATE_DIR, name)
    with open(path, encoding="utf-8") as f:
        return f.read(), os.path.getmtime(path)


def _resolve(name, seen=None):
    """Ghép extends / include thành một khối nguồn duy nhất."""
    seen = seen or set()
    if name in seen:
        raise RuntimeError(f"Vòng lặp include: {name}")
    seen = seen | {name}
    src, mtime = _read(name)
    mtimes = [mtime]

    def inc(m):
        s, ms = _resolve(m.group(1), seen)
        mtimes.extend(ms)
        return s

    m = _EXTENDS.match(src)
    if m:
        child_blocks = {b: body for b, body in _BLOCK.findall(src)}
        parent, ms = _resolve(m.group(1), seen)
        mtimes.extend(ms)
        src = _BLOCK.sub(lambda b: child_blocks.get(b.group(1), b.group(2)), parent)
    else:
        src = _INCLUDE.sub(inc, src)
    src = _INCLUDE.sub(inc, src)
    return src, mtimes


def _split_filters(expr):
    parts = [p.strip() for p in re.split(r"\|(?=\s*[a-z_]+\s*(?:\(|$|\|))", expr)]
    return parts[0], parts[1:]


def _compile(src, name):
    code, ind = [], 0

    def emit(line):
        code.append("    " * ind + line)

    for tok in _TOKEN.split(src):
        if not tok:
            continue
        if tok.startswith("{#"):
            continue
        if tok.startswith("{{"):
            expr, filters = _split_filters(tok[2:-2].strip())
            safe = False
            for f in filters:
                if f == "safe":
                    safe = True
                    continue
                fname, _, args = f.partition("(")
                expr = f"_f_{fname.strip()}({expr}{', ' + args[:-1] if args else ''})"
            emit(f"_w(_s({expr}))" if safe else f"_w(_e({expr}))")
        elif tok.startswith("{%"):
            stmt = tok[2:-2].strip()
            kw = stmt.split(None, 1)[0]
            if kw in ("if", "for"):
                emit(stmt + ":")
                ind += 1
                emit("pass")
            elif kw in ("elif", "else"):
                ind -= 1
                emit(stmt + ":")
                ind += 1
                emit("pass")
            elif kw in ("endif", "endfor"):
                ind -= 1
            elif kw == "set":
                emit(stmt[3:].strip())
            else:
                raise SyntaxError(f"{name}: không hiểu thẻ {{% {stmt} %}}")
        else:
            emit(f"_w({tok!r})")
    if ind != 0:
        raise SyntaxError(f"{name}: thiếu endif/endfor")
    return compile("\n".join(code) or "pass", f"<template {name}>", "exec")


def _e(v):
    if v is None:
        return ""
    if isinstance(v, Markup):
        return str(v)
    return html.escape(str(v), quote=True)


def _s(v):
    return "" if v is None else str(v)


class Markup(str):
    """Chuỗi HTML tin cậy, không cần escape."""


def vnd(n):
    if n is None:
        return ""
    return f"{int(n):,}".replace(",", ".") + "₫"


def num(n):
    return f"{int(n or 0):,}".replace(",", ".")


def rating(x):
    return f"{(x or 0):.1f}".replace(".", ",")


def dt(s, fmt="%d/%m/%Y"):
    from datetime import datetime
    if not s:
        return ""
    try:
        return datetime.fromisoformat(str(s)).strftime(fmt)
    except ValueError:
        return s


FILTERS = {"u": lambda v: __import__("urllib.parse").parse.quote(str(v or "")), "length": len, "vnd": vnd, "num": num, "rating": rating, "dt": dt, "e": _e,
           "default": lambda v, d="": v if v not in (None, "") else d,
           "json": lambda v: Markup(__import__("json").dumps(v, ensure_ascii=False).replace("</", "<\\/"))}

GLOBALS = {"active": "", "vnd": lambda n: vnd(n), "loop_first": lambda x, seq: bool(seq) and seq[0] is x,
           "loop_index": lambda x, seq: next(i for i, y in enumerate(seq) if y is x) + 1}


def render(name, **ctx):
    entry = _cache.get(name)
    if entry:
        files = entry[1]
        if any(os.path.getmtime(os.path.join(config.TEMPLATE_DIR, f)) != t for f, t in files):
            entry = None
    if not entry:
        src, _ = _resolve(name)
        src = _BLOCK.sub(lambda b: b.group(2), src)
        deps = _collect_deps(name)
        entry = (_compile(src, name), deps)
        _cache[name] = entry
    out = []
    env = {"_w": out.append, "_e": _e, "_s": _s}
    env.update({f"_f_{k}": v for k, v in FILTERS.items()})
    env.update(GLOBALS)
    env.update(ctx)
    exec(entry[0], env)
    return "".join(out)


def _collect_deps(name, seen=None):
    seen = seen if seen is not None else []
    if any(n == name for n, _ in seen):
        return seen
    src, mtime = _read(name)
    seen.append((name, mtime))
    for dep in re.findall(r"{%\s*(?:extends|include)\s+[\"'](.+?)[\"']\s*%}", src):
        _collect_deps(dep, seen)
    return seen
