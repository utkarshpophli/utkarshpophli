"""Build the GitHub profile README and its animated SVG cards.

Edit config.json, not this file. Run locally with:
    python scripts/build.py --offline      (uses scripts/sample_data.json)
In GitHub Actions it runs without --offline and pulls live repo data.
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from html import escape as _esc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

TEAL, TEAL_SOFT, WHITE, MUTED, BODY = "#2dd4bf", "#5eead4", "#f0f7f6", "#8fa8a6", "#a3bbb9"
LANG_COLORS = {
    "Python": "#3572A5", "Jupyter Notebook": "#DA5B0B", "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a", "HTML": "#e34c26", "Dart": "#00B4AB", "C++": "#f34b7d",
}


def esc(s):
    return _esc(str(s), quote=True)


# ---------------------------------------------------------------- data
def fetch_repos(user, offline):
    if offline:
        with open(os.path.join(ROOT, "scripts", "sample_data.json"), encoding="utf-8") as f:
            return json.load(f)
    url = f"https://api.github.com/users/{user}/repos?per_page=100&type=owner"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "profile-builder"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def rel_time(iso, now):
    if not iso:
        return ""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    days = (now - dt).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days} days ago"
    if days < 365:
        m = days // 30
        return f"{m} month{'s' if m > 1 else ''} ago"
    y = days // 365
    return f"{y} year{'s' if y > 1 else ''} ago"


# ---------------------------------------------------------------- svg helpers
def text_w(s, size):
    return len(s) * size * 0.56


def wrap(text, size, max_w, max_lines):
    tw = lambda t: len(t) * size * 0.5   # body text runs narrower than pill labels
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if tw(trial) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while tw(lines[-1] + "...") > max_w:
            lines[-1] = lines[-1].rsplit(" ", 1)[0]
        lines[-1] += "..."
    return lines


def clip(s, size, max_w):
    if text_w(s, size) <= max_w:
        return s
    while s and text_w(s + "...", size) > max_w:
        s = s[:-1]
    return s.rstrip() + "..."


STYLE = f"""
<style>
  .f{{font-family:{FONT}}}
  .in{{animation:in .9s cubic-bezier(.16,1,.3,1) both}}
  .d1{{animation-delay:.08s}}.d2{{animation-delay:.16s}}.d3{{animation-delay:.24s}}
  .d4{{animation-delay:.32s}}.d5{{animation-delay:.40s}}.d6{{animation-delay:.48s}}
  .d7{{animation-delay:.56s}}.d8{{animation-delay:.64s}}
  @keyframes in{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
  .drift{{animation:drift 16s ease-in-out infinite alternate}}
  @keyframes drift{{from{{transform:translate(0,0)}}to{{transform:translate(-120px,40px)}}}}
  .sweep{{animation:sweep 7s linear infinite}}
  @keyframes sweep{{from{{stroke-dashoffset:100}}to{{stroke-dashoffset:0}}}}
  .role{{opacity:0;animation:role 9s ease-in-out infinite both}}
  .r1{{opacity:1}}.r2{{animation-delay:3s}}.r3{{animation-delay:6s}}
  @keyframes role{{0%{{opacity:0;transform:translateY(10px)}}5%{{opacity:1;transform:none}}
    30%{{opacity:1;transform:none}}35%{{opacity:0;transform:translateY(-10px)}}100%{{opacity:0}}}}
  .pulse{{animation:pulse 2.4s ease-in-out infinite}}
  @keyframes pulse{{0%,100%{{opacity:.15}}50%{{opacity:.35}}}}
  @media (prefers-reduced-motion:reduce){{
    .in,.drift,.role,.pulse{{animation:none}}.sweep{{display:none}}
  }}
</style>"""


def defs(uid):
    return f"""
<defs>
  <linearGradient id="bg{uid}" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#0a1214"/><stop offset="1" stop-color="#0d2424"/>
  </linearGradient>
  <radialGradient id="ga{uid}" cx="50%" cy="50%" r="50%">
    <stop offset="0" stop-color="{TEAL}" stop-opacity="0.30"/>
    <stop offset="1" stop-color="{TEAL}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="gb{uid}" cx="50%" cy="50%" r="50%">
    <stop offset="0" stop-color="#0f766e" stop-opacity="0.28"/>
    <stop offset="1" stop-color="#0f766e" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="sw{uid}" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{TEAL_SOFT}" stop-opacity="0"/>
    <stop offset=".5" stop-color="{TEAL_SOFT}" stop-opacity="1"/>
    <stop offset="1" stop-color="{TEAL_SOFT}" stop-opacity="0"/>
  </linearGradient>
  <clipPath id="cp{uid}"><rect width="100%" height="100%" rx="16"/></clipPath>
</defs>{STYLE}"""


def frame(uid, w, h, sweep=False):
    s = (f'<g clip-path="url(#cp{uid})">'
         f'<rect width="{w}" height="{h}" fill="url(#bg{uid})"/>'
         f'<g class="drift"><ellipse cx="{w*0.85}" cy="0" rx="{w*0.55}" ry="{h*0.9}" fill="url(#ga{uid})"/></g>'
         f'<ellipse cx="0" cy="{h}" rx="{w*0.5}" ry="{h*0.8}" fill="url(#gb{uid})"/></g>'
         f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="16" fill="none" stroke="{TEAL}" stroke-opacity="0.28"/>')
    if sweep:
        s += (f'<rect class="sweep" x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="16" fill="none" '
              f'stroke="{TEAL_SOFT}" stroke-width="1.5" stroke-opacity="0.9" pathLength="100" '
              f'stroke-dasharray="10 90" stroke-linecap="round"/>')
    return s


def svg(uid, w, h, body, sweep=False, title=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>'
            f'{defs(uid)}{frame(uid, w, h, sweep)}{body}</svg>')


def pills(items, x, y, size=12, accent_first=False, max_x=None):
    out, cx = [], x
    for i, t in enumerate(items):
        w = int(text_w(t, size) + 26)
        if max_x and cx + w > max_x:
            break
        acc = accent_first and i == 0
        out.append(
            f'<rect x="{cx}" y="{y}" width="{w}" height="26" rx="13" fill="{TEAL if acc else "#ffffff"}" '
            f'fill-opacity="{0.16 if acc else 0.05}" stroke="{TEAL}" stroke-opacity="0.30"/>'
            f'<text x="{cx + w/2:.1f}" y="{y + 17}" text-anchor="middle" font-size="{size}" '
            f'fill="#cfe7e4" class="f">{esc(t)}</text>')
        cx += w + 8
    return "".join(out)


def T(x, y, s, size, fill, weight=400, anchor="start", spacing=None, cls="f"):
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" class="{cls}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}"{ls}>{esc(s)}</text>')


def save(name, content):
    with open(os.path.join(ASSETS, name), "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------- cards
def build_header(c):
    W, H = 830, 260
    roles = "".join(
        f'<g class="role r{i+1}">{T(62, 122, r, 18, TEAL_SOFT, 600)}</g>'
        for i, r in enumerate(c["rotating_roles"][:3]))
    pitch = "".join(T(40, 156 + i * 22, line, 15, "#9db4b2") for i, line in enumerate(c["pitch"][:2]))
    certs, y = [], 66
    for i, cert in enumerate(c["certifications"][:2]):
        if i:
            certs.append(f'<line x1="597" y1="{y-18}" x2="772" y2="{y-18}" stroke="{TEAL}" stroke-opacity="0.2"/>')
        for j, line in enumerate(cert["title"]):
            certs.append(T(597, y + 22 + j * 20, line, 16, WHITE, 700))
        y += 22 + (len(cert["title"]) - 1) * 20 + 20
        certs.append(T(597, y, cert["issuer"], 12, MUTED))
        y += 40
    body = f"""
<g class="in">{T(40, 88, c["name"], 42, WHITE, 700)}</g>
<g class="in d1">{T(40, 122, "›", 20, TEAL, 700)}{roles}</g>
<g class="in d2">{pitch}</g>
<g class="in d3">{pills(c["focus_tags"], 40, 204, accent_first=True, max_x=560)}</g>
<g class="in d4">
  <rect x="577" y="36" width="215" height="188" rx="12" fill="#ffffff" fill-opacity="0.04" stroke="{TEAL}" stroke-opacity="0.25"/>
  <circle class="pulse" cx="760" cy="58" r="12" fill="{TEAL}"/>
  <circle cx="760" cy="58" r="4" fill="{TEAL}"/>
  {T(597, 62, "CERTIFIED", 11, TEAL_SOFT, 600, spacing=1.6)}
  {"".join(certs)}
</g>"""
    save("header.svg", svg("h", W, H, body, sweep=True,
                           title=f'{c["name"]}, {c["rotating_roles"][0]}'))


def build_about(c):
    rows = c["about"]
    W, H = 830, 44 + len(rows) * 36
    parts = []
    for i, (label, text) in enumerate(rows):
        y = 52 + i * 36
        parts.append(f'<g class="in d{min(i+1, 8)}">'
                     f'<circle cx="46" cy="{y-5}" r="3.5" fill="{TEAL}"/>'
                     f'{T(62, y, label.upper(), 11, TEAL_SOFT, 600, spacing=1.4)}'
                     f'{T(210, y, clip(text, 15, 580), 15, "#d5e6e3")}</g>')
    save("about.svg", svg("a", W, H, "".join(parts), title="About me"))


def build_card(i, f, repo, c, now):
    W, H = 400, 256
    uid = f"c{i}"
    desc = f.get("description") or (repo or {}).get("description") or ""
    lines = wrap(desc, 14, 344, 3)
    desc_svg = "".join(T(28, 104 + k * 21, l, 14, BODY) for k, l in enumerate(lines))
    if f.get("demo"):
        badge = (f'<rect x="286" y="24" width="90" height="24" rx="12" fill="{TEAL}" fill-opacity="0.16" '
                 f'stroke="{TEAL}" stroke-opacity="0.5"/>'
                 f'{T(331, 40, "LIVE DEMO", 10, TEAL_SOFT, 700, "middle", 1.2)}')
    else:
        badge = T(372, 45, "↗", 18, TEAL_SOFT, 400, "end")

    meta, mx = [], 28
    if repo:
        lang = repo.get("language")
        if lang:
            meta.append(f'<circle cx="{mx+5}" cy="226" r="5" fill="{LANG_COLORS.get(lang, MUTED)}"/>')
            meta.append(T(mx + 16, 230, lang, 12, MUTED))
            mx += 16 + text_w(lang, 12) + 18
        stars = repo.get("stargazers_count", 0)
        if stars >= c.get("min_stars_to_show", 1):
            meta.append(T(mx, 230, f"★ {stars}", 12, TEAL_SOFT, 600))
        when = rel_time(repo.get("pushed_at"), now)
        if when:
            meta.append(T(372, 230, f"Updated {when}", 12, MUTED, 400, "end"))

    body = f"""
<g class="in">
  {T(28, 42, f["label"].upper(), 11, TEAL_SOFT, 600, spacing=1.4)}
  {badge}
  {T(28, 74, f["title"], 23, WHITE, 700)}
</g>
<g class="in d1">{desc_svg}</g>
<g class="in d2">{pills(f.get("stack", []), 28, 166, size=11, max_x=376)}</g>
<line x1="28" y1="206" x2="372" y2="206" stroke="{TEAL}" stroke-opacity="0.14"/>
<g class="in d3">{"".join(meta)}</g>"""
    fname = f"project-{i+1}.svg"
    save(fname, svg(uid, W, H, body, sweep=(i == 0), title=f'{f["title"]}: {desc}'))
    return fname


def build_recent(c, repos, now):
    skip = {c["username"].lower()}
    rs = [r for r in repos if not r.get("fork") and not r.get("archived")
          and r["name"].lower() not in skip and not r.get("private")]
    rs.sort(key=lambda r: r.get("pushed_at") or "", reverse=True)
    rs = rs[: c.get("recent_count", 4)]
    if not rs:
        return None, []
    W, H = 830, 34 + len(rs) * 58
    parts = []
    for i, r in enumerate(rs):
        y = 50 + i * 58
        lang = r.get("language") or ""
        desc = r.get("description") or "No description yet"
        parts.append(
            f'<g class="in d{min(i+1, 8)}">'
            f'{T(40, y, r["name"], 16, WHITE, 700)}'
            f'{T(790, y, rel_time(r.get("pushed_at"), now), 12, TEAL_SOFT, 600, "end")}'
            + (f'<circle cx="45" cy="{y+18}" r="4.5" fill="{LANG_COLORS.get(lang, MUTED)}"/>'
               f'{T(56, y+22, lang, 12, MUTED)}' if lang else "")
            + T(56 + (text_w(lang, 12) + 16 if lang else -16), y + 22, clip(desc, 13, 560), 13, BODY)
            + "</g>")
    save("recent.svg", svg("r", W, H, "".join(parts), title="Recently updated repositories"))
    return "recent.svg", rs


def build_stack(c):
    groups = c["stack"]
    W, H = 830, 30 + len(groups) * 74
    parts = []
    for i, (label, items) in enumerate(groups):
        y = 46 + i * 74
        parts.append(f'<g class="in d{i+1}">{T(40, y, label.upper(), 11, TEAL_SOFT, 600, spacing=1.6)}'
                     f'{pills(items, 40, y + 12, accent_first=(i == 0), max_x=790)}</g>')
    save("stack.svg", svg("s", W, H, "".join(parts), title="Tech stack"))


def build_experience(c):
    rows = c["experience"]
    heights = [76 if r.get("detail") else 54 if r.get("role") else 42 for r in rows]
    W, H = 830, 40 + sum(heights)
    parts, y, ys = [], 52, []
    for i, r in enumerate(rows):
        ys.append(y)
        dot = (f'<circle class="pulse" cx="52" cy="{y-5}" r="11" fill="{TEAL}"/>'
               f'<circle cx="52" cy="{y-5}" r="6" fill="{TEAL}"/>') if i == 0 else \
              f'<circle cx="52" cy="{y-5}" r="5" fill="#0d2424" stroke="{TEAL_SOFT}" stroke-width="2"/>'
        t = T(80, y, r["org"], 17, WHITE, 700)
        if r.get("role"):
            t += T(80, y + 21, r["role"], 13, MUTED)
        if r.get("detail"):
            t += T(80, y + 42, clip(r["detail"], 13, 700), 13, BODY)
        if r.get("when"):
            t += T(790, y, r["when"], 12, TEAL_SOFT, 600, "end")
        parts.append(f'<g class="in d{min(i+1, 8)}">{dot}{t}</g>')
        y += heights[i]
    line = (f'<line x1="52" y1="{ys[0]-5}" x2="52" y2="{ys[-1]-5}" stroke="{TEAL}" '
            f'stroke-opacity="0.3" stroke-width="2"/>')
    save("experience.svg", svg("e", W, H, line + "".join(parts), title="Experience"))


# ---------------------------------------------------------------- readme
def build_readme(c, cards, recent_file, recent_repos):
    u = c["username"]
    badges = "\n".join(
        f'  <a href="{v["url"]}"><img src="https://img.shields.io/badge/{k.replace(" ", "%20")}-0d2424'
        f'?style=for-the-badge&logo={v["logo"]}&logoColor=5eead4" alt="{k}"></a>'
        for k, v in c["links"].items())
    feats = c["featured"]
    rows = []
    for i in range(0, len(feats), 2):
        cells = []
        for j in (i, i + 1):
            if j < len(feats):
                f = feats[j]
                href = f.get("demo") or f"https://github.com/{u}/{f['repo']}"
                cells.append(f'  <a href="{href}"><img src="assets/{cards[j]}" width="49%" '
                             f'alt="{esc(f["title"])}: {esc(f.get("description", ""))}"></a>')
        rows.append('<p align="center">\n' + "\n".join(cells) + "\n</p>")
    demo_src = [f'<a href="https://github.com/{u}/{f["repo"]}">{esc(f["title"])}</a>'
                for f in feats if f.get("demo")]
    src_line = (f'<p align="center"><sub>Source code: {" · ".join(demo_src)}</sub></p>\n'
                if demo_src else "")
    recent = ""
    if recent_file:
        links = " · ".join(f'<a href="{r["html_url"]}">{esc(r["name"])}</a>' for r in recent_repos)
        recent = (f'\n## Recently shipped\n\n<p align="center">\n  <img src="assets/{recent_file}" '
                  f'width="100%" alt="Recently updated repositories">\n</p>\n'
                  f'<p align="center"><sub>{links}</sub></p>\n')
    return f"""<!-- Generated by scripts/build.py. Edit config.json, not this file. -->
<p align="center">
  <img src="assets/header.svg" width="100%" alt="{esc(c['name'])}, {esc(c['rotating_roles'][0])}">
</p>

<p align="center">
{badges}
</p>

## About me

<p align="center">
  <img src="assets/about.svg" width="100%" alt="{esc(' / '.join(f'{a}: {b}' for a, b in c['about']))}">
</p>

## Featured work

{chr(10).join(rows)}
{src_line}{recent}
## Stack

<p align="center">
  <img src="assets/stack.svg" width="100%" alt="{esc(' / '.join(', '.join(g[1]) for g in c['stack']))}">
</p>

## Experience

<p align="center">
  <img src="assets/experience.svg" width="100%" alt="{esc(' / '.join(r['org'] for r in c['experience']))}">
</p>

---

<p align="center">
  {esc(c['footer'])}<br>
  <sub>If a project here helps you, a star helps others find it.</sub>
</p>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="use scripts/sample_data.json")
    args = ap.parse_args()
    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as f:
        c = json.load(f)
    os.makedirs(ASSETS, exist_ok=True)
    try:
        repos = fetch_repos(c["username"], args.offline)
    except Exception as e:  # keep the profile building even if the API hiccups
        print(f"warning: could not fetch repos ({e}); building without live data", file=sys.stderr)
        repos = []
    by_name = {r["name"].lower(): r for r in repos}
    now = datetime.now(timezone.utc)

    build_header(c)
    build_about(c)
    cards = [build_card(i, f, by_name.get(f["repo"].lower()), c, now) for i, f in enumerate(c["featured"])]
    recent_file, recent_repos = build_recent(c, repos, now)
    build_stack(c)
    build_experience(c)
    with open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8") as f:
        f.write(build_readme(c, cards, recent_file, recent_repos))
    print(f"built {len(cards)} project cards, {len(recent_repos)} recent repos")


if __name__ == "__main__":
    main()
