#!/usr/bin/env python3
"""
Draw the profile README's cards as animated SVGs into cards/.

Look: dark cards and light ink, one colour per tile (blue, red, yellow), a big serif name
with an italic surname, and an ASCII portrait that prints itself in.
Fonts: Instrument Serif, Geist and Geist Mono (subset WOFF2s in fonts/, SIL OFL).

GitHub shows each card through <img>, so the SVGs can only use inline CSS
animation, SMIL and fonts embedded as data URIs: no scripts, no external requests.

Inputs:
  data/profile.json        everything personal: name, tiles, stack, featured repos
  data/portrait.txt        ASCII rows for the hero, from make_portrait.py
  data/contributions.json  written daily by fetch_contributions.py (optional; the
                           graph cards show a "syncing" state until it exists)

Set STATIC=1 to render every animation at its final frame (for previews).
"""
import base64
import calendar
import datetime
import json
import os
import re
from html import escape

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "cards")
FONTS = os.path.join(ROOT, "fonts")
PROFILE = json.load(open(os.path.join(ROOT, "data", "profile.json")))
STATIC = bool(os.environ.get("STATIC"))

# ---- tokens -------------------------------------------------------------------
PAPER = "#111214"        # card surface
PAPER_DEEP = "#1f2125"   # empty graph cells
INK = "#f2f2ee"          # main text
INK_SOFT = "#c4c4c0"
MUTED = "#8a8a90"
RULE = "#2a2c31"
BAR_PARTIAL = "#3a3c42"  # the month still in progress
BLUE = "#4a6bff"
RED = "#ef3b2d"
YELLOW = "#ffc81a"
TILE_COLORS = [(BLUE, "#ffffff"), (RED, "#ffffff"), (YELLOW, "#111111")]
HEAT = [PAPER_DEEP, "#1d2b66", "#2a40a3", "#3a5ae0", BLUE, "#9db0ff"]

W = 880          # GitHub's README column at 100%
GAP = 12         # gap between cards, baked in so rows tile exactly
COL = W / 3

SERIF = "'Instrument Serif', Georgia, serif"
SANS = "Geist, system-ui, -apple-system, sans-serif"
MONO = "'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace"
FONT_FILES = {
    "serif": ("Instrument Serif", "normal", 400, "serif-400.woff2"),
    "serif-i": ("Instrument Serif", "italic", 400, "serif-italic.woff2"),
    "sans": ("Geist", "normal", 400, "geist-400.woff2"),
    "sans-b": ("Geist", "normal", 600, "geist-600.woff2"),
    "mono": ("Geist Mono", "normal", 400, "geistmono-400.woff2"),
}

CSS = """
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes pop{0%{opacity:0;transform:scale(.3)}70%{opacity:1;transform:scale(1.15)}100%{opacity:1;transform:none}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
@keyframes nudge{0%,100%{transform:none}50%{transform:translateX(4px)}}
@keyframes nudgeup{0%,100%{transform:none}50%{transform:translate(3px,-3px)}}
@keyframes tilein{0%{opacity:0;transform:translateY(90px) scale(.6) rotate(-9deg)}55%{opacity:1;transform:translateY(-10px) scale(1.05) rotate(2deg)}75%{transform:translateY(3px) scale(.98) rotate(-.8deg)}100%{opacity:1;transform:none}}
@keyframes slidein{from{opacity:0;transform:translateX(-26px)}to{opacity:1;transform:none}}
@keyframes sheen{0%{transform:translateX(-260px) skewX(-20deg)}22%,100%{transform:translateX(420px) skewX(-20deg)}}
@keyframes ring{0%{opacity:.7;transform:scale(.2)}100%{opacity:0;transform:scale(2.4)}}
.r{opacity:0;animation:rise .8s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box}
.f{opacity:0;animation:fade .9s ease-out both}
.g{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow .8s cubic-bezier(.2,.7,.2,1) both}
.p{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .4s ease-out both}
.live{animation:pulse 1.6s ease-in-out infinite}
.n{transform-box:fill-box;animation:nudge 1.8s ease-in-out infinite}
.nu{transform-box:fill-box;animation:nudgeup 1.8s ease-in-out infinite}
.ti{opacity:0;transform-box:fill-box;transform-origin:50% 60%;animation:tilein 1.1s cubic-bezier(.2,.8,.2,1) both}
.sl{opacity:0;transform-box:fill-box;animation:slidein .6s cubic-bezier(.2,.7,.2,1) both}
.sh{animation:sheen 5s ease-in-out infinite}
.rg{opacity:0;transform-box:fill-box;transform-origin:center;animation:ring 1s ease-out both}
@media (prefers-reduced-motion: reduce){.r,.f,.g,.p,.live,.n,.nu,.ti,.sl,.rg{animation:none!important;opacity:1!important;transform:none!important}.sh,.rg{display:none}}
"""
STATIC_CSS = (".r,.f,.g,.p,.live,.n,.nu,.ti,.sl{animation:none!important;opacity:1!important;"
              "transform:none!important}.sh,.rg{display:none}")


def font_css(keys):
    out = []
    for k in keys:
        fam, style, weight, fn = FONT_FILES[k]
        b64 = base64.b64encode(open(os.path.join(FONTS, fn), "rb").read()).decode()
        out.append(f"@font-face{{font-family:'{fam}';font-style:{style};font-weight:{weight};"
                   f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    return "".join(out)


def svg(w, h, body, fonts, label, left=0, right=0, bottom=GAP):
    """A w x h card drawn at x=left on a transparent canvas padded so rows tile exactly."""
    if left:
        body = f'<g transform="translate({left:.3f} 0)">{body}</g>'
    cw, ch = w + left + right, h + bottom
    css = font_css(fonts) + CSS + (STATIC_CSS if STATIC else "")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{cw:.3f}" height="{ch}" '
            f'viewBox="0 0 {cw:.3f} {ch}" role="img" aria-label="{escape(label)}">'
            f'<title>{escape(label)}</title><style>{css}</style>{body}</svg>')


def write(name, content):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w") as f:
        f.write(content)
    print(f"cards/{name}  {len(content) // 1024} KB")


def at(s):
    return f'style="animation-delay:{s:.2f}s"'


def wrap(text, n):
    """Greedy wrap at n characters. A non-breaking space (\\u00a0) keeps two words together."""
    lines, line = [], ""
    for word in text.replace(" ", "\x00").split():
        word = word.replace("\x00", " ")
        if line and len(line) + 1 + len(word) > n:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line] if line else lines


def text_lines(x, y, lines, lh, attrs):
    return "".join(f'<text x="{x}" y="{y + i * lh}" {attrs}>{escape(l)}</text>' for i, l in enumerate(lines))


# ---- hero ---------------------------------------------------------------------
def portrait_rows():
    path = os.path.join(ROOT, "data", "portrait.txt")
    rows = open(path).read().split("\n") if os.path.exists(path) else []
    while rows and not rows[-1].strip():
        rows.pop()
    while rows and not rows[0].strip():
        rows.pop(0)
    return rows


def hero():
    p = PROFILE
    h = 420
    rows = portrait_rows()
    # portrait box on the right, rows centred vertically
    box_x, box_y, box_w, box_h = 500, 28, 352, 364
    cw = box_w / max((len(r) for r in rows), default=1)
    lh = cw * 1.9
    y0 = box_y + (box_h - len(rows) * lh) / 2 + lh * .8
    art = []
    for i, row in enumerate(rows):
        if not row.strip():
            continue
        art.append(f'<text class="f" style="animation-delay:{0.25 + i * 0.03:.3f}s;animation-duration:.35s" '
                   f'xml:space="preserve" x="{box_x}" y="{y0 + i * lh:.2f}" font-size="{cw * 1.62:.2f}" '
                   f'textLength="{len(row) * cw:.1f}" lengthAdjust="spacing" fill="{INK}">{escape(row)}</text>')
    tag = text_lines(48, 338, p["tagline"], 27, f'font-family="{SANS}" font-size="18" fill="{INK_SOFT}"')
    link_w = len(p["link"]) * 7.9
    shine = ('' if STATIC else
             '<animateTransform attributeName="gradientTransform" type="translate" values="-600 0;600 0;600 0" '
             'keyTimes="0;.45;1" dur="7s" begin="1.6s" repeatCount="indefinite"/>')
    body = f"""
<defs>
  <linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="600" y2="0">
    <stop offset="0" stop-color="{INK}"/><stop offset=".42" stop-color="{INK}"/>
    <stop offset=".5" stop-color="{BLUE}"/><stop offset=".58" stop-color="{INK}"/><stop offset="1" stop-color="{INK}"/>
    {shine}
  </linearGradient>
</defs>
<rect width="{W}" height="{h}" rx="14" fill="{PAPER}" stroke="{RULE}"/>
<g class="f" {at(0)}>
  <rect class="live" x="48" y="49" width="8" height="8" rx="2" fill="{BLUE}"/>
  <text x="66" y="57" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">{escape(p["kicker"])}</text>
</g>
<text class="r" {at(0.15)} x="44" y="190" font-family="{SERIF}" font-size="116" letter-spacing="-2.5" fill="{INK}">{escape(p["first_name"])}</text>
<text class="r" {at(0.3)} x="44" y="290" font-family="{SERIF}" font-style="italic" font-size="116" letter-spacing="-2.5" fill="url(#shine)">{escape(p["last_name"])}</text>
<g class="r" {at(0.55)}>{tag}</g>
<g class="f" {at(0.8)}>
  <text x="48" y="396" font-family="{MONO}" font-size="13" fill="{INK}">{escape(p["link"])}</text>
  <text class="nu" x="{48 + link_w + 8:.0f}" y="396" font-family="{MONO}" font-size="13" fill="{BLUE}">&#8599;</text>
</g>
<g font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">{''.join(art)}</g>"""
    write("hero.svg", svg(W, h, body, ["serif", "serif-i", "sans", "mono"],
                          f'{p["first_name"]} {p["last_name"]}. {p["kicker"].title()}. ' + " ".join(p["tagline"])))


# ---- tiles --------------------------------------------------------------------
TILE_W, TILE_H = COL - 8, 210


def count_up(num, word, x, y, attrs, begin, dur=1.1, frames=18):
    """The number counts up from 0 with SMIL <set> frames (works inside <img>), easing out."""
    m = re.match(r"([\d.,]+)(.*)", num)
    tail = f' <tspan font-style="italic">{escape(word)}</tspan>'
    if STATIC or not m:
        return f'<text x="{x}" y="{y}" {attrs}>{escape(num)}{tail}</text>'
    raw, suf = m.group(1).replace(",", ""), m.group(2)
    val = float(raw)
    dec = len(raw.split(".")[1]) if "." in raw else 0
    out = []
    for i in range(frames + 1):
        e = 1 - (1 - i / frames) ** 3
        txt = num if i == frames else f"{val * e:,.{dec}f}{suf}"
        on = begin + dur * i / frames
        off = "" if i == frames else f'<set attributeName="opacity" to="0" begin="{begin + dur * (i + 1) / frames:.3f}s"/>'
        out.append(f'<text x="{x}" y="{y}" {attrs} opacity="0">{escape(txt)}{tail}'
                   f'<set attributeName="opacity" to="1" begin="{on:.3f}s"/>{off}</text>')
    return "".join(out)


def tile_value(tile, live):
    v = str(tile["value"])
    if v.startswith("live:"):
        n = live.get(v[5:])
        return f"{n:,}" if n is not None else "--"
    return v


def tile(i, t, live):
    color, on = TILE_COLORS[i % 3]
    delay = 3.1 + i * 0.25
    num = tile_value(t, live)
    blurb = "".join(
        f'<text class="r" {at(delay + 0.75 + k * 0.1)} x="24" y="{150 + k * 20}" font-family="{SANS}" '
        f'font-size="14" fill="{on}" opacity=".92">{escape(l)}</text>'
        for k, l in enumerate(wrap(t["blurb"], 34)))
    body = f"""
<defs>
  <clipPath id="card"><rect width="{TILE_W:.3f}" height="{TILE_H}" rx="14"/></clipPath>
  <linearGradient id="gl" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>
    <stop offset=".5" stop-color="#fff" stop-opacity=".35"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
</defs>
<g class="ti" {at(delay)}>
  <g clip-path="url(#card)">
    <rect width="{TILE_W:.3f}" height="{TILE_H}" fill="{color}"/>
    <circle class="rg" {at(delay + 0.5)} cx="{TILE_W - 40:.1f}" cy="{TILE_H - 40}" r="60" fill="none" stroke="{on}" stroke-opacity=".5" stroke-width="2"/>
    <rect class="sh" style="animation-delay:{delay + 1.4:.2f}s" x="0" y="-20" width="90" height="{TILE_H + 40}" fill="url(#gl)" transform="translate(-260 0)"/>
  </g>
  <text class="sl" {at(delay + 0.35)} x="24" y="38" font-family="{MONO}" font-size="12" letter-spacing="1.2" fill="{on}">{escape(t["label"])}</text>
  <g class="sl" {at(delay + 0.5)}><text class="n" style="animation-delay:{delay + 1.3:.2f}s" x="{TILE_W - 36:.0f}" y="38" font-family="{MONO}" font-size="14" fill="{on}">&#8594;</text></g>
  {count_up(num, t["word"], 22, 112, f'font-family="{SERIF}" font-size="44" fill="{on}"', delay + 0.45)}
  {blurb}
</g>"""
    write(f"tile-{i + 1}.svg", svg(TILE_W, TILE_H, body, ["serif", "serif-i", "sans", "mono"],
                                   f'{t["label"]}: {num} {t["word"]}. {t["blurb"]}', left=4 * i, right=8 - 4 * i))


# ---- activity -----------------------------------------------------------------
def activity(data):
    h = 340
    year = data["year"] if data else datetime.date.today().year
    now = data["today"][:7] if data else datetime.date.today().strftime("%Y-%m")
    if data:
        monthly = data["monthly"]
        total = f'{data["total"]:,}'
        cur, longest = data["current_streak"], data["longest_streak"]
        note = "current streak, and the longest" if cur >= longest else f"current streak, longest {longest}"
        stats = [(f'{cur} <tspan font-style="italic">days</tspan>', note),
                 (f'{data["active_days"]}<tspan fill="{MUTED}"> / {data["days_so_far"]}</tspan>', "days with a commit"),
                 (str(data["best_day"]["count"]), "on the busiest day")]
    else:
        monthly = [{"month": f"{year}-{k:02d}", "total": 0} for k in range(1, 13)]
        total = "--"
        stats = [("--", "current streak"), ("--", "days with a commit"), ("--", "on the busiest day")]
    done = [m for m in monthly if m["month"] < now]  # finished months; the current one is partial
    current = next((m for m in monthly if m["month"] == now), {"total": 0})
    best = max(done or monthly, key=lambda m: m["total"])
    top = max(best["total"], current["total"], 1)
    x0, x1, base, maxh, gap = 40, 600, 292, 140, 10
    bw = (x1 - x0 - gap * (len(monthly) - 1)) / len(monthly)
    bars = []
    for i, m in enumerate(monthly):
        partial = m["month"] == now
        future = m["month"] > now
        is_best = m is best and m["total"] > 0
        bh = max(4, round(m["total"] / top * maxh))
        x = x0 + i * (bw + gap)
        fill = PAPER_DEEP if future else BLUE if is_best else (BAR_PARTIAL if partial else INK)
        label = calendar.month_abbr[int(m["month"][5:])]
        dl = 2.2 + i * 0.07
        bars.append(f'<rect class="g" {at(dl)} x="{x:.1f}" y="{base - bh}" width="{bw:.1f}" height="{bh}" rx="4" fill="{fill}">'
                    f'<title>{label}: {m["total"]:,}</title></rect>'
                    f'<text class="f" {at(dl)} x="{x + bw / 2:.1f}" y="{base + 22}" text-anchor="middle" '
                    f'font-family="{MONO}" font-size="11" fill="{MUTED}">{label}</text>')
        if is_best:
            bars.append(f'<text class="p" {at(3.2)} x="{x + bw / 2:.1f}" y="{base - bh - 10}" text-anchor="middle" '
                        f'font-family="{MONO}" font-size="11" fill="{BLUE}">{m["total"]:,}</text>')
    side = []
    for i, (big, small) in enumerate(stats):
        y = 104 + i * 92
        side.append(f'<g class="r" {at(2.6 + i * 0.15)}>'
                    f'<text x="650" y="{y}" font-family="{SERIF}" font-size="40" fill="{INK}">{big}</text>'
                    f'<text x="650" y="{y + 24}" font-family="{SANS}" font-size="13" fill="{MUTED}">{small}</text></g>')
        if i < 2:
            side.append(f'<rect class="f" {at(2.6)} x="650" y="{y + 44}" width="190" height="1" fill="{RULE}"/>')
    body = f"""
<rect width="{W}" height="{h}" rx="14" fill="{PAPER}" stroke="{RULE}"/>
<text class="f" {at(1.9)} x="40" y="58" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">{year} ON GITHUB</text>
<text class="r" {at(2.0)} x="38" y="114" font-family="{SERIF}" font-size="52" fill="{INK}">{total} <tspan font-style="italic">contributions</tspan></text>
{''.join(bars)}
{''.join(side)}"""
    write("activity.svg", svg(W, h, body, ["serif", "serif-i", "sans", "mono"],
                              f"{total} contributions in {year}"))


# ---- contribution graph -------------------------------------------------------
def level(c):
    return 0 if c == 0 else 1 if c <= 3 else 2 if c <= 8 else 3 if c <= 15 else 4 if c <= 30 else 5


def placeholder_days():
    d, days = datetime.date(datetime.date.today().year, 1, 1), []
    while d.year == datetime.date.today().year:
        days.append({"date": d.isoformat(), "count": 0})
        d += datetime.timedelta(days=1)
    return days


def heatmap(data):
    days = data["days"] if data else placeholder_days()
    today = data["today"] if data else datetime.date.today().isoformat()
    year = days[0]["date"][:4]
    first = datetime.date.fromisoformat(days[0]["date"])
    lead = (first.weekday() + 1) % 7  # sunday on top, like GitHub
    cell, step, gy = 12, 15, 96
    ncols = (len(days) + lead + 6) // 7
    gx = round((W - ncols * step) / 2)
    cells, months, seen = [], [], set()
    for i, day in enumerate(days):
        col, row = divmod(i + lead, 7)
        date = datetime.date.fromisoformat(day["date"])
        if row == 0 and date.day <= 7 and (date.year, date.month) not in seen:
            seen.add((date.year, date.month))
            months.append((col, date.strftime("%b")))
        c = day["count"]
        future = day["date"] > today  # rest of the year: outlined, not yet filled
        fill = f'fill="none" stroke="{PAPER_DEEP}"' if future else f'fill="{HEAT[level(c)]}"'
        title = "" if future else f'<title>{day["date"]}: {c} contribution{"" if c == 1 else "s"}</title>'
        cells.append(f'<rect class="p" {at(1.0 + col * 0.03 + row * 0.02)} x="{gx + col * step + (0.5 if future else 0)}" '
                     f'y="{gy + row * step + (0.5 if future else 0)}" width="{cell - (1 if future else 0)}" '
                     f'height="{cell - (1 if future else 0)}" rx="3" {fill}>{title}</rect>')
    right = gx + ncols * step - 3
    base = gy + 7 * step
    labels = "".join(f'<text x="{gx + col * step}" y="{base + 16}" font-family="{MONO}" font-size="11" fill="{MUTED}">{m}</text>'
                     for col, m in months if col < ncols - 2)
    # legend sits on its own line under the month labels, so every month keeps its label
    lx = right - len(HEAT) * 14
    ly = base + 26
    legend = "".join(f'<rect x="{lx + i * 14}" y="{ly + 6}" width="11" height="11" rx="2.5" fill="{c}"/>' for i, c in enumerate(HEAT))
    h = ly + 44
    status = f"{year} &#183; REFRESHED DAILY" if data else f"{year} &#183; SYNCING ON FIRST RUN"
    body = f"""
<rect width="{W}" height="{h}" rx="14" fill="{PAPER}" stroke="{RULE}"/>
<text class="r" {at(0.8)} x="{gx - 2}" y="62" font-family="{SERIF}" font-size="34" fill="{INK}">Every day, <tspan font-style="italic" fill="{BLUE}">in blue</tspan></text>
<text class="f" {at(0.8)} x="{right}" y="60" text-anchor="end" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">{status}</text>
{''.join(cells)}
<g class="f" {at(2.4)}>{labels}
<text x="{lx - 8}" y="{ly + 16}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">less</text>{legend}
<text x="{lx + len(HEAT) * 14 + 2}" y="{ly + 16}" font-family="{MONO}" font-size="11" fill="{MUTED}">more</text></g>"""
    total = f'{data["total"]:,} contributions in {year}' if data else "syncing"
    write("heatmap.svg", svg(W, h, body, ["serif", "serif-i", "mono"], f"Contribution graph: {total}"))


# ---- section titles (transparent, so one per GitHub theme) ----------------------
def section_title(slug, text, italic, delay):
    for theme, fg in (("dark", "#e6edf3"), ("light", INK)):
        body = (f'<text class="r" {at(delay)} x="2" y="46" font-family="{SERIF}" font-size="34" fill="{fg}">{escape(text)} '
                f'<tspan font-style="italic">{escape(italic)}</tspan></text>')
        write(f"title-{slug}-{theme}.svg", svg(W, 64, body, ["serif", "serif-i"], f"{text} {italic}", bottom=0))


# ---- repo cards ---------------------------------------------------------------
REPO_W, REPO_H = COL - 8, 176


def repo_card(i, repo, stars):
    color = TILE_COLORS[i % 3][0]
    name = repo.get("title", repo["name"])
    meta = f'{repo["lang"]}  ·  ★ {stars}' if stars else repo["lang"]
    body = f"""
<rect width="{REPO_W:.3f}" height="{REPO_H}" rx="14" fill="{PAPER}" stroke="{RULE}"/>
<g class="r" {at(4.6 + i * 0.12)}>
  <rect x="24" y="30" width="8" height="8" rx="2" fill="{color}"/>
  <text x="40" y="39" font-family="{SANS}" font-weight="600" font-size="18" fill="{INK}">{escape(name)}</text>
  {text_lines(24, 72, wrap(repo["desc"], 34), 21, f'font-family="{SANS}" font-size="14" fill="{INK_SOFT}"')}
  <text x="24" y="{REPO_H - 24}" font-family="{MONO}" font-size="12" fill="{MUTED}">{escape(meta)}</text>
</g>"""
    write(f"repo-{i + 1}.svg", svg(REPO_W, REPO_H, body, ["sans", "sans-b", "mono"], f'{name}: {repo["desc"]}',
                                   left=4 * i, right=8 - 4 * i))


# ---- stack --------------------------------------------------------------------
def stack():
    rows, y = [], 34
    groups = PROFILE["stack"]
    for r, (group, items) in enumerate(groups):
        color = TILE_COLORS[r % 3][0]
        rows.append(f'<g class="r" {at(5.2 + r * 0.1)}>'
                    f'<rect x="24" y="{y + 9}" width="8" height="8" rx="2" fill="{color}"/>'
                    f'<text x="40" y="{y + 18}" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">{escape(group.upper())}</text>'
                    f'<text x="180" y="{y + 18}" font-family="{SANS}" font-size="15" fill="{INK}">{escape("  ·  ".join(items))}</text></g>')
        if r < len(groups) - 1:
            rows.append(f'<rect class="f" {at(5.2)} x="24" y="{y + 36}" width="{W - 48}" height="1" fill="{RULE}"/>')
        y += 46
    h = y + 22
    body = f'<rect width="{W}" height="{h}" rx="14" fill="{PAPER}" stroke="{RULE}"/>{"".join(rows)}'
    flat = "; ".join(f"{g}: {', '.join(i)}" for g, i in groups)
    write("stack.svg", svg(W, h, body, ["sans", "mono"], f"Tech stack. {flat}"))


# ---- live numbers from the GitHub API -------------------------------------------
def github_numbers():
    """Public repo count, and stars per featured repo. Empty when offline."""
    try:
        import requests
    except ImportError:
        return {}, {}
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f'Bearer {os.environ["GITHUB_TOKEN"]}'
    user, live, stars = PROFILE["username"], {}, {}
    try:
        r = requests.get(f"https://api.github.com/users/{user}", headers=headers, timeout=10)
        if r.ok:
            live["repos"] = r.json().get("public_repos")
        for repo in PROFILE["repos"]:
            r = requests.get(f'https://api.github.com/repos/{user}/{repo["name"]}', headers=headers, timeout=10)
            if r.ok:
                stars[repo["name"]] = r.json().get("stargazers_count", 0)
    except Exception as e:
        print(f"github api unavailable: {e}")
    return live, stars


if __name__ == "__main__":
    path = os.path.join(ROOT, "data", "contributions.json")
    data = json.load(open(path)) if os.path.exists(path) else None
    live, stars = github_numbers()
    if data:
        live["contributions"] = data["total"]
    hero()
    for i, t in enumerate(PROFILE["tiles"][:3]):
        tile(i, t, live)
    activity(data)
    heatmap(data)
    section_title("coding", "What I'm", "coding", 4.4)
    for i, repo in enumerate(PROFILE["repos"][:3]):
        repo_card(i, repo, stars.get(repo["name"]))
    section_title("stack", "What I", "use", 5.0)
    stack()
