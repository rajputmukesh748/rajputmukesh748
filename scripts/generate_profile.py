#!/usr/bin/env python3
"""Generate all self-hosted profile SVGs (no third-party image widgets).

Pulls public data from GitHub (REST API + public contribution calendar) and
writes SVG files into ./assets. Standard library only.
Usage: GITHUB_TOKEN=... python3 scripts/generate_profile.py [username]
"""
import base64, html, json, os, random, re, sys, urllib.request
from datetime import date, timedelta

USER = sys.argv[1] if len(sys.argv) > 1 else "rajputmukesh748"
NAME = "Mukesh Kumar"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
os.makedirs(OUT, exist_ok=True)
MONO = "font-family=\"'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif\""
SANS = "font-family=\"'Segoe UI','Helvetica Neue',Arial,sans-serif\""
C1, C2, C3, GR = "#7aa2ff", "#c4a3ff", "#ff7eb3", "#8affd1"
ORG = "#ff9a5a"
BG, CARD = "#0b1020", "#121a33"
esc = html.escape


def get(url, raw=False):
    h = {"User-Agent": "profile-svg-generator"}
    tok = os.environ.get("GITHUB_TOKEN")
    if tok and "api.github.com" in url:
        h["Authorization"] = "Bearer " + tok
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=20) as r:
        d = r.read()
    return d if raw else json.loads(d)


def safe(fn, default):
    try:
        return fn()
    except Exception as e:  # network / rate limit: keep generating with fallbacks
        print("warn:", e)
        return default


def write(name, svg):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", name)


# ------------------------------------------------------------------ data
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".profile_cache.json")
cache = safe(lambda: json.load(open(CACHE)), {})
user = safe(lambda: get(f"https://api.github.com/users/{USER}"), {})
repos = safe(lambda: get(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner"), [])
api_ok = bool(user) and bool(repos)
own = [r for r in repos if not r.get("fork")]
langs, lang_ok = {}, api_ok
if api_ok:
    for r in own[:60]:
        l = safe(lambda: get(r["languages_url"]), None)
        if l is None:
            lang_ok = False
            break
        for k, v in l.items():
            langs[k] = langs.get(k, 0) + v
if api_ok:
    stars = sum(r.get("stargazers_count", 0) for r in own)
    n_repos, followers = user.get("public_repos", len(repos)), user.get("followers", 0)
else:  # rate-limited / offline: reuse the last good numbers instead of showing zeros
    stars, n_repos, followers = cache.get("stars", 0), cache.get("repos", 0), cache.get("followers", 0)
if not lang_ok or not langs:
    langs = cache.get("langs", {})
tot = sum(langs.values()) or 1
top_langs = sorted(((k, v) for k, v in langs.items() if k != "Other"), key=lambda kv: -kv[1])[:6]

# contribution calendar (public page, no auth needed)
cells, total_year = {}, 0
page = safe(lambda: get(f"https://github.com/users/{USER}/contributions", raw=True).decode("utf-8"), "")
counts = {}
for m in re.finditer(r'for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]*)<', page):
    t = m.group(2)
    n = re.match(r"(\d+) contribution", t)
    counts[m.group(1)] = int(n.group(1)) if n else 0
for m in re.finditer(r"<td\b[^>]*>", page):
    tag = m.group(0)
    i = re.search(r'id="contribution-day-component-(\d+)-(\d+)"', tag)
    d = re.search(r'data-date="([\d-]+)"', tag)
    lv = re.search(r'data-level="(\d)"', tag)
    if i and d and lv:
        row, col = int(i.group(1)), int(i.group(2))
        c = counts.get(f"contribution-day-component-{row}-{col}", 0)
        cells[(col, row)] = (d.group(1), int(lv.group(1)), c)
        total_year += c

days = sorted((v[0], v[2]) for v in cells.values())
longest = cur = run = 0
for dt, c in days:
    run = run + 1 if c > 0 else 0
    longest = max(longest, run)
cur = 0
for dt, c in reversed(days):
    if c > 0:
        cur += 1
    elif dt == days[-1][0]:
        continue  # today may still be empty
    else:
        break

avatar_b64 = cache.get("avatar", "")
if api_ok and user.get("avatar_url"):
    avatar_b64 = safe(lambda: base64.b64encode(get(user["avatar_url"] + ("&" if "?" in user["avatar_url"] else "?") + "s=200", raw=True)).decode(), avatar_b64)
if api_ok:
    json.dump({"stars": stars, "repos": n_repos, "followers": followers, "langs": langs, "avatar": avatar_b64}, open(CACHE, "w"))

# ------------------------------------------------------------------ header
def header():
    W, H = 1000, 330
    lines = ["Crafting scalable Android apps", "Clean architecture  •  Clean code", "Kotlin  •  Compose  •  SwiftUI  •  Node.js", "Generative AI  •  Agentic AI", "Always learning. Always shipping."]
    n = len(lines); cyc = n * 3; sub = ""
    for i, l in enumerate(lines):
        kt = f"0;{i/n:.3f};{(i+0.12)/n:.3f};{(i+0.88)/n:.3f};{(i+1)/n:.3f};1"
        sub += (f'<text x="590" y="222" text-anchor="middle" fill="#dbe4ff" font-size="21" {SANS} opacity="0">{esc(l)}'
                f'<animate attributeName="opacity" dur="{cyc}s" repeatCount="indefinite" keyTimes="{kt}" values="0;0;1;1;0;0"/></text>')
    av = ""
    if avatar_b64:
        av = (f'<circle cx="150" cy="165" r="104" fill="none" stroke="url(#ring)" stroke-width="4"/>'
              f'<circle cx="150" cy="165" r="112" fill="none" stroke="url(#ring)" stroke-opacity="0.35" stroke-width="2" stroke-dasharray="3 9"><animateTransform attributeName="transform" type="rotate" from="0 150 165" to="360 150 165" dur="30s" repeatCount="indefinite"/></circle>'
              f'<clipPath id="av"><circle cx="150" cy="165" r="96"/></clipPath>'
              f'<image href="data:image/jpeg;base64,{avatar_b64}" x="54" y="69" width="192" height="192" clip-path="url(#av)" preserveAspectRatio="xMidYMid slice"/>')
    pills = ""
    px = 400
    for label, col in [("Android Engineer", C3), ("India", C1), ("Open to collaborate", GR)]:
        w = int(len(label) * 8 + 34)
        pills += (f'<rect x="{px}" y="262" width="{w}" height="30" rx="15" fill="{col}" fill-opacity="0.14" stroke="{col}" stroke-opacity="0.7"/>'
                  f'<text x="{px+w/2}" y="282" text-anchor="middle" fill="{col}" font-size="13" font-weight="600" {SANS}>{label}</text>')
        px += w + 12
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>
<linearGradient id="ring" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{ORG}"/><stop offset="0.5" stop-color="{C3}"/><stop offset="1" stop-color="{C2}"/></linearGradient>
<linearGradient id="name" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#ffd6e8"/></linearGradient>
<linearGradient id="line" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{ORG}"/><stop offset="0.5" stop-color="{C3}"/><stop offset="1" stop-color="{C2}"/></linearGradient>
<filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="55"/></filter>
<clipPath id="rc"><rect width="{W}" height="{H}" rx="24"/></clipPath>
</defs>
<g clip-path="url(#rc)">
<rect width="{W}" height="{H}" fill="{BG}"/>
<g filter="url(#blur)">
<circle cx="140" cy="90" r="130" fill="{C3}" opacity="0.55"><animate attributeName="cx" values="140;300;140" dur="16s" repeatCount="indefinite"/></circle>
<circle cx="520" cy="320" r="140" fill="{ORG}" opacity="0.45"><animate attributeName="cy" values="320;230;320" dur="13s" repeatCount="indefinite"/></circle>
<circle cx="880" cy="60" r="150" fill="{C2}" opacity="0.55"><animate attributeName="cx" values="880;700;880" dur="18s" repeatCount="indefinite"/></circle>
<circle cx="780" cy="300" r="120" fill="{C1}" opacity="0.45"><animate attributeName="cx" values="780;900;780" dur="15s" repeatCount="indefinite"/></circle>
</g>
<rect width="{W}" height="{H}" fill="{BG}" opacity="0.28"/>
{av}
<text x="590" y="108" text-anchor="middle" fill="#e8ecff" fill-opacity="0.75" font-size="15" letter-spacing="8" {SANS}>HI, I'M</text>
<text x="590" y="178" text-anchor="middle" font-size="70" font-weight="800" fill="url(#name)" {SANS}>Mukesh Kumar</text>
<rect x="470" y="192" width="240" height="4" rx="2" fill="url(#line)"/>
{sub}
{pills}
</g>
<rect x="1.5" y="1.5" width="{W-3}" height="{H-3}" rx="23" fill="none" stroke="url(#line)" stroke-opacity="0.8" stroke-width="2"/>
</svg>'''


# ------------------------------------------------------------------ about (bento)
def about():
    W, H = 1000, 596
    def card(x, y, w, h, col, title, body):
        return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{CARD}" stroke="{col}" stroke-opacity="0.5"/>'
                f'<rect x="{x+22}" y="{y+22}" width="30" height="4" rx="2" fill="{col}"/>'
                f'<text x="{x+22}" y="{y+52}" fill="{col}" font-size="13" font-weight="700" letter-spacing="2" {SANS}>{title.upper()}</text>{body}')
    def t(x, y, s, size=15, col="#d6def5", wt="400"):
        return f'<text x="{x}" y="{y}" fill="{col}" font-size="{size}" font-weight="{wt}" {SANS}>{esc(s)}</text>'
    # about card
    ab = (t(42, 118, "A developer who loves building scalable, real-world", 20, "#fff", "600")
          + t(42, 146, "applications, solving complex problems and exploring", 20, "#fff", "600")
          + t(42, 174, "new technologies.", 20, "#fff", "600")
          + t(42, 212, "Android engineer building with clean architectures — and now with AI.", 14, "#9fb0d9"))
    cx = 42
    for a, col in [("MVI", C3), ("Clean Architecture", ORG), ("MVVM", C2), ("MVP", C1), ("MVC", GR)]:
        w = int(len(a) * 8.6 + 28)
        ab += (f'<rect x="{cx}" y="236" width="{w}" height="30" rx="15" fill="{col}" fill-opacity="0.15" stroke="{col}" stroke-opacity="0.7"/>'
               f'<text x="{cx+w/2}" y="256" text-anchor="middle" fill="{col}" font-size="13" font-weight="600" {SANS}>{a}</text>')
        cx += w + 10
    cx = 42
    for a, col in [("AI", GR), ("Generative AI", C1), ("Agentic AI", C3)]:
        w = int(len(a) * 8.6 + 28)
        ab += (f'<rect x="{cx}" y="282" width="{w}" height="30" rx="15" fill="{col}" fill-opacity="0.15" stroke="{col}" stroke-opacity="0.7"/>'
               f'<text x="{cx+w/2}" y="302" text-anchor="middle" fill="{col}" font-size="13" font-weight="600" {SANS}>{a}</text>')
        cx += w + 10
    focus = ""
    items = [("Android apps: Kotlin & Compose", True), ("Scalable MVI · Clean · MVVM", True), ("iOS & cross-platform: SwiftUI, KMP", True), ("Backend & APIs: Node.js, Ktor", True), ("Generative & Agentic AI solutions", True), ("Performance, quality & clean code", True)]
    for i, (txt, done) in enumerate(items):
        y = 106 + i * 36
        col = GR if done else "#5b6b99"
        focus += (f'<circle cx="{660+14}" cy="{y-5}" r="10" fill="{col}" fill-opacity="{0.18 if done else 0.1}" stroke="{col}"/>'
                  + (f'<path d="M{660+9} {y-5}l4 4 7-8" fill="none" stroke="{col}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>' if done else "")
                  + t(660+34, y, txt, 14.5, "#e8ecff" if done else "#8b99c4"))
    out = card(20, 20, 600, 320, C3, "About me", ab) + card(640, 20, 340, 320, GR, "What I do best", focus)
    # lower row
    bw = 232; gap = 17
    boxes = [
        ("Building", C1, ["Android apps at scale", "Clean, testable code", "Cross-platform products"]),
        ("Exploring", C2, ["Generative AI", "Agentic AI workflows", "Backend with Node.js"]),
        ("Open to collaborate", ORG, ["Android projects", "SwiftUI & iOS apps", "Node.js & AI products"]),
        ("Ask me about", C3, ["Android architectures", "Design patterns", "Kotlin", "Generative & agentic AI"]),
    ]
    for i, (ttl, col, its) in enumerate(boxes):
        x = 20 + i * (bw + gap)
        body = "".join(f'<circle cx="{x+30}" cy="{y0-5}" r="3.5" fill="{col}"/>' + t(x+44, y0, s, 14.5, "#e8ecff")
                       for s, y0 in [(s, 112 + 28 * j) for j, s in enumerate(its)]) if False else ""
        for j, s in enumerate(its):
            y0 = 328 + 82 + 0  # placeholder replaced below
        out += card(x, 360, bw, 180, col, ttl, "".join(
            f'<circle cx="{x+27}" cy="{360+78+j*23-5}" r="3.2" fill="{col}"/>' + t(x+38, 360+78+j*23, s, 14, "#e8ecff") for j, s in enumerate(its)))
    out += (f'<rect x="20" y="436" width="960" height="2" rx="1" fill="url(#ln)" opacity="0.0"/>')
    foot = t(500, 572, "I love exploring new tech and building efficient solutions.", 14, "#9fb0d9").replace("<text ", '<text text-anchor="middle" ', 1)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs><linearGradient id="ln" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{ORG}"/><stop offset="1" stop-color="{C2}"/></linearGradient></defs>
<rect width="{W}" height="{H}" rx="24" fill="{BG}"/>
{out}{foot}
</svg>'''


# ------------------------------------------------------------------ stack
def stack():
    cats = [
        ("MOBILE", [("Android", "#3DDC84", "#000"), ("Kotlin", "#7F52FF", "#fff"), ("Jetpack Compose", "#4285F4", "#fff"), ("KMP", "#7F52FF", "#fff"), ("Compose MP", "#4285F4", "#fff"), ("Swift", "#F54A2A", "#fff"), ("SwiftUI", "#0D96F6", "#fff"), ("Flutter", "#02569B", "#fff"), ("React Native", "#20c4e8", "#000")]),
        ("BACKEND", [("Java", "#ED8B00", "#000"), ("Spring Boot", "#6DB33F", "#000"), ("Ktor", "#087CFA", "#fff"), ("Node.js", "#339933", "#fff"), ("Express", "#6b7785", "#fff"), ("GraphQL", "#E10098", "#fff"), ("Apollo", "#5b3fd1", "#fff"), ("Firebase", "#FFCA28", "#000")]),
        ("FRONTEND", [("HTML5", "#E34F26", "#fff"), ("CSS3", "#1572B6", "#fff"), ("SCSS", "#CC6699", "#fff"), ("Bootstrap", "#7952B3", "#fff"), ("JavaScript", "#F7DF1E", "#000"), ("TypeScript", "#3178C6", "#fff"), ("React", "#20c4e8", "#000"), ("Angular", "#DD0031", "#fff")]),
        ("DATA", [("MySQL", "#4479A1", "#fff"), ("MongoDB", "#47A248", "#fff"), ("Firebase", "#FFCA28", "#000")]),
        ("DEVOPS", [("Git", "#F05032", "#fff"), ("GitHub", "#30363d", "#fff"), ("GitLab CI", "#FC6D26", "#000"), ("Bitbucket", "#0052CC", "#fff"), ("AWS", "#FF9900", "#000"), ("Heroku", "#6762A6", "#fff")]),
        ("TOOLS", [("Android Studio", "#3DDC84", "#000"), ("Postman", "#FF6C37", "#000"), ("Swagger", "#85EA2D", "#000"), ("SonarQube", "#4E9BCD", "#000"), ("Socket.io", "#4b5563", "#fff"), ("JWT", "#d63aff", "#fff"), ("Figma", "#F24E1E", "#fff")]),
        ("AI", [("Generative AI", "#00b8d4", "#000"), ("Agentic AI", "#ff4081", "#fff"), ("LLMs", "#7c4dff", "#fff"), ("Prompt Engineering", "#c4a3ff", "#000"), ("Claude Code", "#D97757", "#000")]),
    ]
    SW, y, body, k = 1000, 24, "", 0
    for cat, items in cats:
        body += f'<text x="24" y="{y+22}" fill="#8b949e" font-size="12" letter-spacing="3" {MONO}>{cat}</text>'
        x = 170
        for name, bg, fg in items:
            w = int(len(name) * 8.4 + 28)
            if x + w > SW - 20:
                x = 170; y += 40
            body += (f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{k*0.05:.2f}s" dur="0.4s" fill="freeze"/>'
                     f'<rect x="{x}" y="{y}" width="{w}" height="30" rx="15" fill="{bg}"/>'
                     f'<text x="{x+w/2}" y="{y+20}" text-anchor="middle" fill="{fg}" font-size="13" font-weight="700" {MONO}>{esc(name)}</text></g>')
            x += w + 10; k += 1
        y += 54
    SH = y + 6
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SW} {SH}" width="{SW}" height="{SH}">
<defs><linearGradient id="b" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{C2}"/><stop offset="1" stop-color="{C1}"/></linearGradient></defs>
<rect x="1" y="1" width="{SW-2}" height="{SH-2}" rx="14" fill="#0b1020" stroke="url(#b)" stroke-width="2"/>
{body}
</svg>'''


# ------------------------------------------------------------------ stats HUD
def stats():
    W = 1000
    tiles = [("CONTRIBUTIONS", f"{total_year:,}", "last 12 months", C1), ("REPOSITORIES", str(n_repos), "public", C2),
             ("STARS", str(stars), "earned", "#ffcb6b"), ("FOLLOWERS", str(followers), "developers", C3), ("ACTIVE DAYS", str(sum(1 for _, c in days if c > 0)), "last 12 months", GR)]
    tw, gap = 176, 15
    t = ""
    for i, (lab, val, sub, col) in enumerate(tiles):
        x = 20 + i * (tw + gap)
        t += (f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{i*0.15:.2f}s" dur="0.5s" fill="freeze"/>'
              f'<rect x="{x}" y="20" width="{tw}" height="110" rx="12" fill="#121a33" stroke="{col}" stroke-opacity="0.7"/>'
              f'<rect x="{x}" y="20" width="{tw}" height="4" rx="2" fill="{col}"/>'
              f'<text x="{x+tw/2}" y="52" text-anchor="middle" fill="#8b949e" font-size="11" letter-spacing="2" {MONO}>{lab}</text>'
              f'<text x="{x+tw/2}" y="94" text-anchor="middle" fill="{col}" font-size="38" font-weight="800" {SANS}>{val}</text>'
              f'<text x="{x+tw/2}" y="116" text-anchor="middle" fill="#6b7280" font-size="11" {MONO}>{sub}</text></g>')
    # languages
    lb = f'<text x="30" y="176" fill="#e6edf3" font-size="15" font-weight="700" {MONO}>TOP LANGUAGES</text>'
    pal = [C3, ORG, C2, C1, GR, "#ffcb6b"]
    for i, (name, v) in enumerate(top_langs or [("n/a", 1)]):
        y = 205 + i * 30; pct = v / tot * 100; bw = max(4, int(pct / 100 * 360))
        lb += (f'<text x="30" y="{y+12}" fill="#c9d1d9" font-size="13" {MONO}>{esc(name)}</text>'
               f'<rect x="150" y="{y}" width="360" height="14" rx="7" fill="#1f2937"/>'
               f'<rect x="150" y="{y}" width="{bw}" height="14" rx="7" fill="{pal[i%6]}"><animate attributeName="width" from="0" to="{bw}" dur="1.2s" fill="freeze"/></rect>'
               f'<text x="525" y="{y+12}" fill="#8b949e" font-size="12" {MONO}>{pct:.1f}%</text>')
    # streak ring
    cx, cy, r = 780, 245, 62
    circ = 2 * 3.14159 * r; frac = min(cur / 30, 1) if cur else 0.02
    ring = (f'<text x="780" y="176" text-anchor="middle" fill="#e6edf3" font-size="15" font-weight="700" {MONO}>STREAK</text>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#1f2937" stroke-width="12"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#sr)" stroke-width="12" stroke-linecap="round" stroke-dasharray="{circ*frac:.1f} {circ:.1f}" transform="rotate(-90 {cx} {cy})"><animate attributeName="stroke-dasharray" from="0 {circ:.1f}" to="{circ*frac:.1f} {circ:.1f}" dur="1.4s" fill="freeze"/></circle>'
            f'<text x="{cx}" y="{cy+8}" text-anchor="middle" fill="#fff" font-size="30" font-weight="800" {SANS}>{cur}</text>'
            f'<text x="{cx}" y="{cy+28}" text-anchor="middle" fill="#8b949e" font-size="10" letter-spacing="2" {MONO}>DAYS</text>'
            f'<text x="{cx}" y="{cy+95}" text-anchor="middle" fill="#8b949e" font-size="12" {MONO}>longest streak: {longest} days</text>')
    H = 372
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs><linearGradient id="b" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{C1}"/><stop offset="1" stop-color="{C3}"/></linearGradient>
<linearGradient id="sr" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C1}"/><stop offset="1" stop-color="{C3}"/></linearGradient></defs>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="#0b1020" stroke="url(#b)" stroke-width="2"/>
{t}{lb}{ring}
<text x="{W-20}" y="{H-14}" text-anchor="end" fill="#4b5563" font-size="10" {MONO}>auto-generated from GitHub data</text>
</svg>'''


# ------------------------------------------------------------------ heatmap
def heatmap():
    cs, gap = 14, 3
    cols = (max(c for c, _ in cells) + 1) if cells else 53
    W = 28 + cols * (cs + gap) + 30; H = 210
    lv = ["#161d36", "#5b2a55", "#a8408a", C3, ORG]
    g = ""
    for (c, r), (d, l, n) in sorted(cells.items()):
        x, y = 36 + c * (cs + gap), 52 + r * (cs + gap)
        g += (f'<rect x="{x}" y="{y}" width="{cs}" height="{cs}" rx="3" fill="{lv[l]}" opacity="0">'
              f'<animate attributeName="opacity" from="0" to="1" begin="{c*0.02:.2f}s" dur="0.3s" fill="freeze"/><title>{n} contributions on {d}</title></rect>')
    months = ""
    seen = set()
    for (c, r), (d, l, n) in sorted(cells.items()):
        if r == 0:
            mname = date.fromisoformat(d).strftime("%b")
            if mname not in seen:
                seen.add(mname)
                months += f'<text x="{36+c*(cs+gap)}" y="44" fill="#8b949e" font-size="11" {MONO}>{mname}</text>'
    legend = "".join(f'<rect x="{W-200+i*18}" y="{H-30}" width="14" height="14" rx="3" fill="{lv[i]}"/>' for i in range(5))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs><linearGradient id="b" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{C2}"/><stop offset="1" stop-color="{C1}"/></linearGradient></defs>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="#0b1020" stroke="url(#b)" stroke-width="2"/>
<text x="24" y="28" fill="#e6edf3" font-size="14" font-weight="700" {MONO}>{total_year:,} contributions in the last year</text>
{months}{g}
<text x="{W-215}" y="{H-18}" text-anchor="end" fill="#8b949e" font-size="11" {MONO}>less</text>{legend}<text x="{W-104}" y="{H-18}" fill="#8b949e" font-size="11" {MONO}>more</text>
</svg>'''


# ------------------------------------------------------------------ footer
def footer():
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 140" width="1000" height="140" preserveAspectRatio="none">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{ORG}"/><stop offset="0.5" stop-color="{C3}"/><stop offset="1" stop-color="{C2}"/></linearGradient></defs>
<path fill="url(#g)" fill-opacity="0.35"><animate attributeName="d" dur="9s" repeatCount="indefinite" values="M0 70 Q250 20 500 70 T1000 70 V140 H0Z;M0 70 Q250 120 500 70 T1000 70 V140 H0Z;M0 70 Q250 20 500 70 T1000 70 V140 H0Z"/></path>
<path fill="url(#g)" fill-opacity="0.6"><animate attributeName="d" dur="6s" repeatCount="indefinite" values="M0 95 Q250 55 500 95 T1000 95 V140 H0Z;M0 95 Q250 135 500 95 T1000 95 V140 H0Z;M0 95 Q250 55 500 95 T1000 95 V140 H0Z"/></path>
<text x="500" y="124" text-anchor="middle" fill="#ffffff" font-size="15" letter-spacing="4" font-family="'Segoe UI',Arial,sans-serif">THANKS FOR VISITING</text>
</svg>'''


for fname, fn in [("header.svg", header), ("about.svg", about), ("stack.svg", stack),
                  ("stats.svg", stats), ("heatmap.svg", heatmap), ("footer.svg", footer)]:
    write(fname, fn())
print(f"contrib={total_year} repos={n_repos} stars={stars} followers={followers} streak={cur}/{longest} langs={[l for l,_ in top_langs]}")
