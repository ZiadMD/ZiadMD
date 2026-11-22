#!/usr/bin/env python3
"""
Draw the profile README's cards as animated SVGs into cards/.

Design: "Night shift". A dark terminal, one lime-green signal colour (the same
#32CD32 the old README used) plus amber and cyan for the other two roles.
JetBrains Mono for anything a machine would print, Space Grotesk for headlines.

GitHub shows each card through <img>, so the SVGs can only use inline CSS
animation, SMIL and fonts embedded as data URIs: no scripts, no external requests.

Inputs:
  data/profile.json        everything personal: name, roles, stack, featured repos
  data/contributions.json  written daily by fetch_contributions.py (optional; the
                           graph cards show a "syncing" state until it exists)

Set STATIC=1 to render every animation at its final frame (for previews).
"""
import base64
import calendar
import datetime
import json
import os
from html import escape

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "cards")
FONTS = os.path.join(ROOT, "fonts")
PROFILE = json.load(open(os.path.join(ROOT, "data", "profile.json")))
STATIC = bool(os.environ.get("STATIC"))

# ---- tokens -------------------------------------------------------------------
BG = "#0a0e0b"
PANEL = "#111712"
PANEL_HI = "#172019"
LINE = "#223026"
TEXT = "#e9f5ea"
SOFT = "#b4c4b7"
MUTED = "#73867a"
GREEN = "#32cd32"
AMBER = "#ffb020"
CYAN = "#38c8f0"
ROLE_COLORS = [GREEN, AMBER, CYAN]
HEAT = ["#18211a", "#174d1c", "#1f7a24", "#28a82c", GREEN, "#7cf27c"]

W = 880          # GitHub's README column at 100%
GAP = 12         # gap between cards, baked in so rows tile exactly
COL = W / 3

MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace"
DISPLAY = "'Space Grotesk', system-ui, -apple-system, sans-serif"
FONT_FILES = {
    "mono": ("JetBrains Mono", 400, "mono-400.woff2"),
    "mono-b": ("JetBrains Mono", 700, "mono-700.woff2"),
    "disp": ("Space Grotesk", 500, "grotesk-500.woff2"),
    "disp-b": ("Space Grotesk", 700, "grotesk-700.woff2"),
}

CSS = """
@keyframes up{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes in{from{opacity:0}to{opacity:1}}
@keyframes bar{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes dot{0%{opacity:0;transform:scale(0)}70%{opacity:1;transform:scale(1.25)}100%{opacity:1;transform:none}}
@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}
@keyframes breathe{0%,100%{opacity:1}50%{opacity:.3}}
@keyframes scan{0%{transform:translateY(-40px)}100%{transform:translateY(460px)}}
@keyframes wipe{from{transform:scaleX(0)}to{transform:scaleX(1)}}
.u{opacity:0;animation:up .7s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box}
.i{opacity:0;animation:in .6s ease-out both}
.b{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:bar .7s cubic-bezier(.2,.7,.2,1) both}
.d{opacity:0;transform-box:fill-box;transform-origin:center;animation:dot .35s ease-out both}
.w{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:wipe .9s cubic-bezier(.2,.7,.2,1) both}
.cur{animation:blink 1.1s steps(1) infinite}
.live{animation:breathe 1.8s ease-in-out infinite}
.scan{animation:scan 6s linear infinite}
@media (prefers-reduced-motion: reduce){.u,.i,.b,.d,.w{animation:none!important;opacity:1!important;transform:none!important}.scan{display:none}}
"""
STATIC_CSS = ".u,.i,.b,.d,.w{animation:none!important;opacity:1!important;transform:none!important}.scan,.cur{display:none}"


def font_css(keys):
    out = []
    for k in keys:
        fam, weight, fn = FONT_FILES[k]
        b64 = base64.b64encode(open(os.path.join(FONTS, fn), "rb").read()).decode()
        out.append(f"@font-face{{font-family:'{fam}';font-weight:{weight};"
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
    """Greedy wrap at n characters. A non-breaking space (\u00a0) keeps two words together."""
    lines, line = [], ""
    for word in text.replace("\u00a0", "\x00").split():
        word = word.replace("\x00", " ")
        if line and len(line) + 1 + len(word) > n:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line] if line else lines


def panel(w, h, cid):
    """Rounded dark panel with a faint dot grid and a slow scanline."""
    return f"""
<defs>
  <clipPath id="{cid}"><rect width="{w:.3f}" height="{h}" rx="14"/></clipPath>
  <pattern id="{cid}g" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="{LINE}"/></pattern>
  <linearGradient id="{cid}s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GREEN}" stop-opacity="0"/>
    <stop offset="1" stop-color="{GREEN}" stop-opacity=".07"/></linearGradient>
</defs>
<g clip-path="url(#{cid})">
  <rect width="{w:.3f}" height="{h}" fill="{BG}"/>
  <rect width="{w:.3f}" height="{h}" fill="url(#{cid}g)" opacity=".55"/>
  <rect class="scan" y="0" width="{w:.3f}" height="40" fill="url(#{cid}s)"/>
</g>
<rect x=".5" y=".5" width="{w - 1:.3f}" height="{h - 1}" rx="13.5" fill="none" stroke="{LINE}"/>"""


def kicker(x, y, text, color=GREEN, delay=0.0, live=True):
    sq = f'<rect class="live" x="{x}" y="{y - 9}" width="8" height="8" rx="1" fill="{color}"/>' if live else ""
    tx = x + 16 if live else x
    return (f'<g class="i" {at(delay)}>{sq}<text x="{tx}" y="{y}" font-family="{MONO}" font-size="12" '
            f'letter-spacing="1.2" fill="{MUTED}">{escape(text)}</text></g>')


# ---- hero ---------------------------------------------------------------------
def hero():
    p = PROFILE
    h = 400
    # terminal window on the right
    tx, ty, tw, th = 472, 44, 368, 312
    lines, y, t = [], ty + 66, 0.9
    for kind, text in p["terminal"]:
        if kind == "cmd":
            t += 0.35
            chars = len(text)
            dur = 0.04 * chars + 0.1
            clip = f"tc{len(lines)}"
            lines.append(
                f'<clipPath id="{clip}"><rect x="{tx + 40}" y="{y - 14}" height="20" width="{0 if not STATIC else 300}">'
                + ("" if STATIC else
                   f'<animate attributeName="width" from="0" to="{chars * 7.8 + 4:.0f}" begin="{t:.2f}s" dur="{dur:.2f}s" '
                   f'calcMode="discrete" values="{";".join(str(round(k * 7.8)) for k in range(chars + 1))}" fill="freeze"/>')
                + "</rect></clipPath>"
                f'<g class="i" {at(t)}><text x="{tx + 22}" y="{y}" font-family="{MONO}" font-size="13" fill="{GREEN}">$</text></g>'
                f'<text clip-path="url(#{clip})" x="{tx + 40}" y="{y}" font-family="{MONO}" font-size="13" fill="{TEXT}">{escape(text)}</text>'
            )
            t += dur + 0.15
        else:
            lines.append(f'<text class="i" {at(t)} x="{tx + 22}" y="{y}" xml:space="preserve" '
                         f'font-family="{MONO}" font-size="12.5" fill="{SOFT}">{escape(text)}</text>')
            t += 0.12
        y += 23 if kind == "out" else 25
    lines.append(f'<g class="i" {at(t)}><text x="{tx + 22}" y="{y}" font-family="{MONO}" font-size="13" fill="{GREEN}">$</text>'
                 f'<rect class="cur" x="{tx + 40}" y="{y - 12}" width="8" height="15" fill="{GREEN}"/></g>')
    term = f"""
<g class="u" {at(0.5)}>
  <rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="10" fill="{PANEL}" stroke="{LINE}"/>
  <path d="M{tx} {ty + 34}h{tw}" stroke="{LINE}"/>
  <circle cx="{tx + 20}" cy="{ty + 17}" r="5" fill="#ff5f57"/><circle cx="{tx + 38}" cy="{ty + 17}" r="5" fill="#febc2e"/>
  <circle cx="{tx + 56}" cy="{ty + 17}" r="5" fill="{GREEN}"/>
  <text x="{tx + tw / 2}" y="{ty + 21}" text-anchor="middle" font-family="{MONO}" font-size="11" fill="{MUTED}">ziad@dev: ~</text>
</g>
{''.join(lines)}"""
    tag = "".join(
        f'<text x="44" y="{300 + i * 26}" font-family="{DISPLAY}" font-size="17" fill="{SOFT}">{escape(l)}</text>'
        for i, l in enumerate(p["tagline"]))
    body = f"""{panel(W, h, 'hc')}
<defs><linearGradient id="nm" x1="0" x2="1"><stop offset="0" stop-color="{GREEN}"/><stop offset="1" stop-color="#9dff6a"/></linearGradient></defs>
{kicker(44, 66, p["kicker"], delay=0)}
<text class="u" {at(0.1)} x="40" y="158" font-family="{DISPLAY}" font-weight="700" font-size="84" letter-spacing="-3" fill="{TEXT}">{escape(p["first_name"])}</text>
<text class="u" {at(0.25)} x="40" y="238" font-family="{DISPLAY}" font-weight="700" font-size="84" letter-spacing="-3" fill="url(#nm)">{escape(p["last_name"])}<tspan fill="{TEXT}">.</tspan></text>
<g class="u" {at(0.45)}>{tag}</g>
<g class="i" {at(0.7)}><text x="44" y="364" font-family="{MONO}" font-size="12" fill="{MUTED}">~/github/<tspan fill="{TEXT}">{escape(p["username"])}</tspan></text></g>
{term}"""
    write("hero.svg", svg(W, h, body, ["mono", "disp-b", "disp"],
                          f'{p["first_name"]} {p["last_name"]}. ' + " ".join(p["tagline"])))


# ---- role tiles ---------------------------------------------------------------
TILE_W, TILE_H = COL - 8, 206


def role_tile(i, role):
    color = ROLE_COLORS[i % 3]
    delay = 0.2 + i * 0.15
    blurb = "".join(
        f'<text x="22" y="{154 + k * 19}" font-family="{DISPLAY}" font-size="13.5" fill="{SOFT}">{escape(l)}</text>'
        for k, l in enumerate(wrap(role["blurb"], 35)))
    body = f"""{panel(TILE_W, TILE_H, f'rt{i}')}
<g clip-path="url(#rt{i})"><rect class="w" {at(delay + 0.2)} x="0" y="0" width="{TILE_W:.3f}" height="3" fill="{color}"/></g>
<g class="u" {at(delay)}>
  <text x="22" y="38" font-family="{MONO}" font-size="11.5" letter-spacing="1.2" fill="{color}">0{i + 1} / {escape(role["label"])}</text>
  <text x="22" y="88" font-family="{DISPLAY}" font-weight="700" font-size="25" letter-spacing="-.5" fill="{TEXT}">{escape(role["title"])}</text>
  <text x="22" y="114" font-family="{MONO}" font-size="12.5" fill="{color}">{escape(role["tools"])}</text>
</g>
<g class="i" {at(delay + 0.4)}>{blurb}</g>"""
    write(f"role-{i + 1}.svg", svg(TILE_W, TILE_H, body, ["mono", "disp", "disp-b"],
                                   f'{role["title"]} ({role["tools"]}). {role["blurb"]}',
                                   left=4 * i, right=8 - 4 * i))


# ---- contribution graph -------------------------------------------------------
def level(c, top):
    if c == 0:
        return 0
    q = c / max(top, 1)
    return 1 if q <= .1 else 2 if q <= .25 else 3 if q <= .5 else 4 if q <= .8 else 5


def placeholder_days():
    end = datetime.date.today()
    return [{"date": (end - datetime.timedelta(days=k)).isoformat(), "count": 0} for k in range(370, -1, -1)]


def heatmap(data):
    days = data["days"] if data else placeholder_days()
    counts = sorted(d["count"] for d in days if d["count"])
    top = counts[int(len(counts) * .95)] if counts else 1  # one huge day shouldn't flatten the rest
    first = datetime.date.fromisoformat(days[0]["date"])
    lead = (first.weekday() + 1) % 7  # sunday on top, like GitHub
    ncols = (len(days) + lead + 6) // 7
    cell, step, gy = 11, 14, 100
    gx = round((W - ncols * step) / 2) + 10  # centred, nudged right for the weekday labels
    cells, months, seen = [], [], set()
    for k, day in enumerate(days):
        col, row = divmod(k + lead, 7)
        date = datetime.date.fromisoformat(day["date"])
        if row == 0 and date.day <= 7 and (date.year, date.month) not in seen:
            seen.add((date.year, date.month))
            months.append((col, date.strftime("%b")))
        c = day["count"]
        cells.append(
            f'<rect class="d" {at(0.6 + col * 0.025 + row * 0.02)} x="{gx + col * step}" y="{gy + row * step}" '
            f'width="{cell}" height="{cell}" rx="2.5" fill="{HEAT[level(c, top)]}">'
            f'<title>{day["date"]}: {c} contribution{"" if c == 1 else "s"}</title></rect>')
    right = gx + ncols * step - 3
    base = gy + 7 * step
    labels = "".join(f'<text x="{gx + col * step}" y="{base + 18}" font-family="{MONO}" font-size="11" fill="{MUTED}">{m}</text>'
                     for col, m in months if col < ncols - 10)
    lx = right - len(HEAT) * 14
    legend = "".join(f'<rect x="{lx + k * 14}" y="{base + 8}" width="11" height="11" rx="2" fill="{c}"/>' for k, c in enumerate(HEAT))
    for k, wd in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        labels += f'<text x="{gx - 8}" y="{gy + k * step + 9}" text-anchor="end" font-family="{MONO}" font-size="10" fill="{MUTED}">{wd}</text>'
    h = base + 46
    status = "SYNCING ON FIRST RUN" if not data else f'UPDATED {data["generated_at"][:10]}'
    body = f"""{panel(W, h, 'hm')}
<text class="u" {at(0.3)} x="{gx - 2}" y="64" font-family="{DISPLAY}" font-weight="700" font-size="30" letter-spacing="-.8" fill="{TEXT}">git log <tspan fill="{GREEN}">--every-day</tspan></text>
<g class="i" {at(0.3)}><text x="{right}" y="62" text-anchor="end" font-family="{MONO}" font-size="11.5" letter-spacing="1" fill="{MUTED}">{status}</text></g>
{''.join(cells)}
<g class="i" {at(1.8)}>{labels}
<text x="{lx - 8}" y="{base + 18}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">less</text>{legend}
<text x="{lx + len(HEAT) * 14 + 2}" y="{base + 18}" font-family="{MONO}" font-size="11" fill="{MUTED}">more</text></g>"""
    total = f'{data["total"]:,} contributions in the last year' if data else "Contribution graph, syncing"
    write("heatmap.svg", svg(W, h, body, ["mono", "disp-b"], f"Contribution graph: {total}"))


# ---- activity -----------------------------------------------------------------
def activity(data):
    h = 330
    if data:
        monthly = data["monthly"][-12:]
        total, cur, longest = f'{data["total"]:,}', data["current_streak"], data["longest_streak"]
        stats = [(str(cur), "day streak right now"), (str(longest), "longest streak"),
                 (str(data["best_day"]["count"]), "on the busiest day")]
    else:
        today = datetime.date.today().replace(day=1)
        monthly, m = [], today
        for _ in range(12):
            monthly.insert(0, {"month": m.strftime("%Y-%m"), "total": 0})
            m = (m - datetime.timedelta(days=1)).replace(day=1)
        total, stats = "--", [("--", "day streak right now"), ("--", "longest streak"), ("--", "on the busiest day")]
    best = max(monthly[:-1] or monthly, key=lambda m: m["total"])
    top = max(best["total"], monthly[-1]["total"], 1)
    x0, x1, base, maxh, gap = 42, 590, 280, 130, 10
    bw = (x1 - x0 - gap * (len(monthly) - 1)) / len(monthly)
    bars = []
    for k, m in enumerate(monthly):
        bh = max(4, round(m["total"] / top * maxh))
        x = x0 + k * (bw + gap)
        is_best = m is best and m["total"] > 0
        fill = GREEN if is_best else ("#2b3a2e" if k == len(monthly) - 1 else "#3f5a44")
        name = calendar.month_abbr[int(m["month"][5:])]
        dl = 0.5 + k * 0.06
        bars.append(f'<rect class="b" {at(dl)} x="{x:.1f}" y="{base - bh}" width="{bw:.1f}" height="{bh}" rx="3" fill="{fill}">'
                    f'<title>{name}: {m["total"]:,}</title></rect>'
                    f'<text class="i" {at(dl)} x="{x + bw / 2:.1f}" y="{base + 20}" text-anchor="middle" '
                    f'font-family="{MONO}" font-size="10.5" fill="{MUTED}">{name}</text>')
        if is_best:
            bars.append(f'<text class="d" {at(1.5)} x="{x + bw / 2:.1f}" y="{base - bh - 9}" text-anchor="middle" '
                        f'font-family="{MONO}" font-size="11" fill="{GREEN}">{m["total"]:,}</text>')
    side = [f'<rect x="628" y="40" width="1" height="{h - 80}" fill="{LINE}"/>']
    for k, (big, small) in enumerate(stats):
        y = 102 + k * 82
        color = [GREEN, AMBER, CYAN][k]
        side.append(f'<g class="u" {at(1.0 + k * 0.15)}>'
                    f'<text x="656" y="{y}" font-family="{DISPLAY}" font-weight="700" font-size="38" letter-spacing="-1" fill="{TEXT}">{big}</text>'
                    f'<rect x="657" y="{y + 14}" width="7" height="7" rx="1" fill="{color}"/>'
                    f'<text x="672" y="{y + 21}" font-family="{MONO}" font-size="11.5" fill="{MUTED}">{small}</text></g>')
    body = f"""{panel(W, h, 'ac')}
{kicker(44, 56, "THE LAST 12 MONTHS", delay=0.2, live=False)}
<text class="u" {at(0.3)} x="42" y="104" font-family="{DISPLAY}" font-weight="700" font-size="40" letter-spacing="-1.2" fill="{TEXT}">{total} <tspan fill="{GREEN}">commits &amp; co.</tspan></text>
{''.join(bars)}
{''.join(side)}"""
    write("activity.svg", svg(W, h, body, ["mono", "disp-b"], f"{total} contributions in the last 12 months"))


# ---- stack --------------------------------------------------------------------
def stack():
    rows, y, k = [], 96, 0
    for r, (group, items) in enumerate(PROFILE["stack"]):
        color = ROLE_COLORS[r % 3]
        rows.append(f'<text class="i" {at(0.3 + r * 0.1)} x="44" y="{y + 18}" font-family="{MONO}" font-size="12" fill="{MUTED}">{escape(group)}</text>')
        x = 190
        for item in items:
            w = len(item) * 7.6 + 26
            rows.append(f'<g class="u" {at(0.35 + r * 0.1 + k * 0.012)}>'
                        f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="27" rx="6" fill="{PANEL_HI}" stroke="{LINE}"/>'
                        f'<circle cx="{x + 11:.1f}" cy="{y + 13.5}" r="2.5" fill="{color}"/>'
                        f'<text x="{x + 19:.1f}" y="{y + 18}" font-family="{MONO}" font-size="12" fill="{TEXT}">{escape(item)}</text></g>')
            x += w + 8
            k += 1
        y += 40
    h = y + 26
    body = f"""{panel(W, h, 'st')}
<text class="u" {at(0.1)} x="42" y="62" font-family="{DISPLAY}" font-weight="700" font-size="30" letter-spacing="-.8" fill="{TEXT}">ls <tspan fill="{GREEN}">~/stack</tspan></text>
{''.join(rows)}"""
    flat = "; ".join(f"{g}: {', '.join(i)}" for g, i in PROFILE["stack"])
    write("stack.svg", svg(W, h, body, ["mono", "disp-b"], f"Tech stack. {flat}"))


# ---- projects -----------------------------------------------------------------
REPO_W, REPO_H = COL - 8, 180


def projects_title():
    h = 60
    body = f"""{panel(W, h, 'pt')}
<text class="u" {at(0.1)} x="42" y="38" font-family="{DISPLAY}" font-weight="700" font-size="22" letter-spacing="-.5" fill="{TEXT}">cd <tspan fill="{GREEN}">~/projects</tspan></text>
<g class="i" {at(0.2)}><text x="{W - 40}" y="36" text-anchor="end" font-family="{MONO}" font-size="11.5" letter-spacing="1" fill="{MUTED}">WHAT I'M BUILDING</text></g>"""
    write("projects.svg", svg(W, h, body, ["mono", "disp-b"], "Projects: what I'm building"))


def repo_card(i, repo, stars):
    color = ROLE_COLORS[i % 3]
    name = repo.get("title", repo["name"])
    meta = f'{repo["lang"]}' + (f"  ·  ★ {stars}" if stars else "")
    desc = "".join(f'<text x="22" y="{84 + k * 20}" font-family="{DISPLAY}" font-size="13.5" fill="{SOFT}">{escape(l)}</text>'
                   for k, l in enumerate(wrap(repo["desc"], 36)))
    body = f"""{panel(REPO_W, REPO_H, f'rp{i}')}
<g class="u" {at(0.2 + i * 0.12)}>
  <text x="22" y="40" font-family="{MONO}" font-size="12" fill="{MUTED}">ZiadMD/</text>
  <text x="22" y="62" font-family="{DISPLAY}" font-weight="700" font-size="19" letter-spacing="-.3" fill="{TEXT}">{escape(name)}</text>
  {desc}
  <circle cx="27" cy="{REPO_H - 27}" r="4.5" fill="{color}"/>
  <text x="38" y="{REPO_H - 23}" font-family="{MONO}" font-size="11.5" fill="{MUTED}">{escape(meta)}</text>
  <text x="{REPO_W - 22:.1f}" y="{REPO_H - 23}" text-anchor="end" font-family="{MONO}" font-size="13" fill="{color}">&#8599;</text>
</g>"""
    write(f"repo-{i + 1}.svg", svg(REPO_W, REPO_H, body, ["mono", "disp", "disp-b"], f'{name}: {repo["desc"]}',
                                   left=4 * i, right=8 - 4 * i))


def repo_stars():
    try:
        import requests
    except ImportError:
        return {}
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f'Bearer {os.environ["GITHUB_TOKEN"]}'
    stars = {}
    for repo in PROFILE["repos"]:
        try:
            r = requests.get(f'https://api.github.com/repos/{PROFILE["username"]}/{repo["name"]}', headers=headers, timeout=10)
            if r.ok:
                stars[repo["name"]] = r.json().get("stargazers_count", 0)
        except Exception as e:  # offline: render without stars
            print(f"stars unavailable for {repo['name']}: {e}")
    return stars


if __name__ == "__main__":
    path = os.path.join(ROOT, "data", "contributions.json")
    data = json.load(open(path)) if os.path.exists(path) else None
    hero()
    for i, role in enumerate(PROFILE["roles"][:3]):
        role_tile(i, role)
    heatmap(data)
    activity(data)
    stack()
    projects_title()
    stars = repo_stars()
    for i, repo in enumerate(PROFILE["repos"][:3]):
        repo_card(i, repo, stars.get(repo["name"]))
