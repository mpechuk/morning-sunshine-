#!/usr/bin/env python3
"""
The Morning Sunshine — Daily Happy News Generator
Fetches positive news RSS feeds, uses Claude API to format 10 stories,
then writes a self-contained index.html for GitHub Pages.

Requirements: pip install anthropic
Env var:      ANTHROPIC_API_KEY
"""

import anthropic
import datetime
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


# ---------------------------------------------------------------------------
# 1. RSS FETCHING
# ---------------------------------------------------------------------------

RSS_FEEDS = [
    ("https://www.goodnewsnetwork.org/feed/", "Good News Network"),
    ("https://www.positive.news/feed/", "Positive News"),
    ("https://www.sunnyskyz.com/rss.php", "Sunny Skyz"),
]


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()


def fetch_rss_stories() -> list[dict]:
    stories = []
    for url, source in RSS_FEEDS:
        try:
            req = Request(url, headers={"User-Agent": "MorningSunshine/1.0"})
            with urlopen(req, timeout=15) as resp:
                raw = resp.read()
            root = ET.fromstring(raw)
            items = root.findall(".//item")[:10]
            for item in items:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                desc = _strip_html(item.findtext("description") or "")[:400]
                if title and link:
                    stories.append({"title": title, "link": link,
                                    "description": desc, "source": source})
        except Exception as exc:
            print(f"[warn] Could not fetch {url}: {exc}", file=sys.stderr)
    return stories


# ---------------------------------------------------------------------------
# 2. CLAUDE — generate 10 story objects
# ---------------------------------------------------------------------------

def _load_newspaper_def() -> str:
    """Read story schema fields from newspaper.md."""
    md_path = os.path.join(os.path.dirname(__file__), "newspaper.md")
    with open(md_path, encoding="utf-8") as f:
        content = f.read()
    # Extract the Story Schema table rows into a compact JSON-schema description
    lines = [l for l in content.splitlines() if l.startswith("| `")]
    fields = {}
    for line in lines:
        parts = [p.strip() for p in line.strip("|").split("|")]
        key = parts[0].strip("`")
        fields[key] = parts[1]
    return json.dumps(fields, indent=2)

STORY_SCHEMA = _load_newspaper_def()

CATEGORY_STYLES = {
    "Science":     ("#3b82f6", "linear-gradient(135deg,#1e3a8a,#3b82f6)"),
    "Animals":     ("#16a34a", "linear-gradient(135deg,#052e16,#16a34a)"),
    "Kindness":    ("#ec4899", "linear-gradient(135deg,#831843,#ec4899)"),
    "Funny":       ("#f59e0b", "linear-gradient(135deg,#78350f,#f59e0b)"),
    "Sports":      ("#8b5cf6", "linear-gradient(135deg,#4c1d95,#8b5cf6)"),
    "Community":   ("#06b6d4", "linear-gradient(135deg,#164e63,#06b6d4)"),
    "Environment": ("#22c55e", "linear-gradient(135deg,#14532d,#22c55e)"),
    "Arts":        ("#f97316", "linear-gradient(135deg,#7c2d12,#f97316)"),
    "Tech":        ("#6366f1", "linear-gradient(135deg,#312e81,#6366f1)"),
    "Health":      ("#ef4444", "linear-gradient(135deg,#7f1d1d,#ef4444)"),
}
DEFAULT_STYLE = ("#d97706", "linear-gradient(135deg,#78350f,#d97706)")


def generate_stories(client: anthropic.Anthropic, rss_stories: list[dict],
                     today_str: str) -> list[dict]:
    if rss_stories:
        context = ("Here are real stories from today's positive news RSS feeds:\n"
                   + json.dumps(rss_stories[:20], indent=2)
                   + "\n\nSelect the best 10 and rewrite them in newspaper style.")
    else:
        context = ("No RSS feed was available today. "
                   "Based on your knowledge of recent genuinely uplifting world events, "
                   "write 10 diverse real positive stories.")

    prompt = (
        f"You are the editor of 'The Morning Sunshine,' a newspaper that publishes "
        f"ONLY happy, optimistic, funny, or uplifting news. Today is {today_str}.\n\n"
        f"{context}\n\n"
        f"Return ONLY a valid JSON array of exactly 10 objects — no markdown fences, "
        f"no extra text. Each object must match this schema:\n{STORY_SCHEMA}\n"
        f"Ensure diverse categories across the 10 stories."
    )

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


# ---------------------------------------------------------------------------
# 3. HTML GENERATION
# ---------------------------------------------------------------------------

CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:Georgia,'Times New Roman',serif;background:#fef9f0;color:#1a1a1a;line-height:1.6}
.masthead{background:#1c1917;color:#fef9f0;text-align:center;border-bottom:4px solid #d97706}
.masthead-top{padding:24px 20px 16px;border-bottom:1px solid rgba(255,255,255,.15)}
.edition-label{font-size:.7rem;letter-spacing:3px;text-transform:uppercase;color:#d97706;margin-bottom:8px;font-family:system-ui,sans-serif}
.newspaper-name{font-size:clamp(2.4rem,8vw,5rem);font-weight:900;letter-spacing:-2px;color:#fbbf24;text-shadow:0 2px 20px rgba(251,191,36,.3);font-style:italic;line-height:1}
.motto{font-size:.95rem;font-style:italic;color:rgba(255,255,255,.65);margin-top:6px;letter-spacing:2px}
.masthead-meta{display:flex;justify-content:space-between;align-items:center;padding:10px 28px;font-size:.78rem;color:rgba(255,255,255,.55);font-family:system-ui,sans-serif}
.masthead-meta .date{font-weight:700;color:#fbbf24;font-size:.85rem}
.ticker{background:#d97706;color:#fff;padding:8px 0;text-align:center;font-size:.8rem;font-weight:700;letter-spacing:3px;text-transform:uppercase;font-family:system-ui,sans-serif}
.container{max-width:1200px;margin:0 auto;padding:36px 16px}
.featured{display:grid;grid-template-columns:1fr 1fr;background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 4px 28px rgba(0,0,0,.1);margin-bottom:44px}
@media(max-width:760px){.featured{grid-template-columns:1fr}}
.featured-img{display:flex;align-items:center;justify-content:center;padding:60px 40px;min-height:340px}
.featured-emoji{font-size:7.5rem;filter:drop-shadow(0 8px 28px rgba(0,0,0,.35))}
.featured-body{padding:40px;display:flex;flex-direction:column;justify-content:center;border-left:4px solid #d97706}
.badge{display:inline-block;font-size:.65rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:3px 12px;border-radius:20px;color:#fff;margin-bottom:14px;font-family:system-ui,sans-serif}
.featured-body h2{font-size:clamp(1.45rem,3vw,2.4rem);line-height:1.2;margin-bottom:12px;font-weight:900}
.featured-body .deck{font-size:1.05rem;color:#4b5563;font-style:italic;margin-bottom:18px;line-height:1.55}
.featured-body .story-text p{font-size:.93rem;color:#374151;margin-bottom:10px;line-height:1.72}
.section-divider{text-align:center;margin:0 0 32px;position:relative}
.section-divider::before{content:'';position:absolute;top:50%;left:0;right:0;height:1px;background:#d1d5db}
.section-divider span{position:relative;background:#fef9f0;padding:0 20px;font-size:.7rem;letter-spacing:4px;text-transform:uppercase;color:#9ca3af;font-family:system-ui,sans-serif}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
@media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:580px){.grid{grid-template-columns:1fr}}
.card{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 14px rgba(0,0,0,.07);display:flex;flex-direction:column;transition:transform .2s,box-shadow .2s}
.card:hover{transform:translateY(-4px);box-shadow:0 10px 32px rgba(0,0,0,.12)}
.card-img{display:flex;align-items:center;justify-content:center;padding:28px 20px;min-height:150px}
.card-emoji{font-size:3.8rem;filter:drop-shadow(0 4px 10px rgba(0,0,0,.28))}
.card-content{padding:18px 20px 20px;flex:1;display:flex;flex-direction:column}
.card-headline{font-size:1rem;font-weight:800;line-height:1.3;margin-bottom:7px}
.card-deck{font-size:.82rem;color:#4b5563;font-style:italic;margin-bottom:10px;line-height:1.5}
.card-text{font-size:.8rem;color:#374151;line-height:1.65;flex:1}
.card-text p{margin-bottom:7px}
a.source{display:inline-flex;align-items:center;gap:5px;font-size:.72rem;color:#9ca3af;text-decoration:none;margin-top:12px;padding-top:12px;border-top:1px solid #f3f4f6;font-family:system-ui,sans-serif;transition:color .2s}
a.source:hover{color:#d97706}
a.source::before{content:'→'}
footer{text-align:center;padding:40px 20px;color:#9ca3af;font-size:.78rem;font-family:system-ui,sans-serif;border-top:1px solid #e5e7eb;margin-top:20px}
footer strong{color:#d97706}
footer a{color:#d97706}
"""


def _paras(text: str) -> str:
    """Wrap each double-newline-separated chunk in <p> tags."""
    parts = [p.strip() for p in re.split(r"\n{2,}", text.strip()) if p.strip()]
    if not parts:
        return f"<p>{text.strip()}</p>"
    return "".join(f"<p>{p}</p>" for p in parts)


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def build_card(story: dict) -> str:
    cat = story.get("category", "Community")
    color, gradient = CATEGORY_STYLES.get(cat, DEFAULT_STYLE)
    return (
        f'<article class="card">\n'
        f'  <div class="card-img" style="background:{gradient}">'
        f'<span class="card-emoji">{story["emoji"]}</span></div>\n'
        f'  <div class="card-content">\n'
        f'    <span class="badge" style="background:{color}">{_esc(cat)}</span>\n'
        f'    <h3 class="card-headline">{_esc(story["headline"])}</h3>\n'
        f'    <p class="card-deck">{_esc(story["deck"])}</p>\n'
        f'    <div class="card-text">{_paras(story["body"])}</div>\n'
        f'    <a class="source" href="{_esc(story["sourceUrl"])}" '
        f'target="_blank" rel="noopener">{_esc(story["sourceName"])}</a>\n'
        f'  </div>\n</article>'
    )


def build_featured(story: dict) -> str:
    cat = story.get("category", "Science")
    color, gradient = CATEGORY_STYLES.get(cat, DEFAULT_STYLE)
    return (
        f'<article class="featured">\n'
        f'  <div class="featured-img" style="background:{gradient}">'
        f'<span class="featured-emoji">{story["emoji"]}</span></div>\n'
        f'  <div class="featured-body">\n'
        f'    <span class="badge" style="background:{color}">{_esc(cat)}</span>\n'
        f'    <h2>{_esc(story["headline"])}</h2>\n'
        f'    <p class="deck">{_esc(story["deck"])}</p>\n'
        f'    <div class="story-text">{_paras(story["body"])}</div>\n'
        f'    <a class="source" href="{_esc(story["sourceUrl"])}" '
        f'target="_blank" rel="noopener">{_esc(story["sourceName"])}</a>\n'
        f'  </div>\n</article>'
    )


def build_html(stories: list[dict], date_str: str) -> str:
    featured = build_featured(stories[0])
    cards = "\n".join(build_card(s) for s in stories[1:])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Morning Sunshine \u2014 {date_str}</title>
<style>{CSS}</style>
</head>
<body>
<header class="masthead">
  <div class="masthead-top">
    <p class="edition-label">Est. 2026 \u00b7 Good News Only \u00b7 Vol. 1</p>
    <h1 class="newspaper-name">The Morning Sunshine</h1>
    <p class="motto">\u201cAll the news that\u2019s fit to smile about\u201d</p>
  </div>
  <div class="masthead-meta">
    <span>Daily Edition</span>
    <span class="date">{date_str}</span>
    <span>\u2600\ufe0f Sunny Skies Ahead</span>
  </div>
</header>
<div class="ticker">\u2728 Today\u2019s Edition: 10 Stories Guaranteed to Brighten Your Day \u2728</div>
<main class="container">
{featured}
<div class="section-divider"><span>More Good News</span></div>
<div class="grid">
{cards}
</div>
</main>
<footer>
  <strong>The Morning Sunshine</strong> \u00b7 All the news that\u2019s fit to smile about<br>
  Published daily at 7 AM \u00b7 Powered by real good news &amp; \u2600\ufe0f \u00b7
  <a href="https://github.com/mpechuk/morning-sunshine-">GitHub</a>
</footer>
</body>
</html>"""


# ---------------------------------------------------------------------------
# 4. MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    today = datetime.date.today()
    date_str = today.strftime("%A, %B %d, %Y")
    print(f"[info] Generating newspaper for {date_str}")

    print("[info] Fetching RSS feeds...")
    rss_stories = fetch_rss_stories()
    print(f"[info] Got {len(rss_stories)} RSS stories")

    print("[info] Calling Claude API...")
    client = anthropic.Anthropic(api_key=api_key)
    stories = generate_stories(client, rss_stories, date_str)
    print(f"[info] Generated {len(stories)} stories")

    html = build_html(stories, date_str)
    out_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[info] Written to {out_path}")


if __name__ == "__main__":
    main()
