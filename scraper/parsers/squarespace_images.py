"""Parser for restaurants that post their menu as photos on a Squarespace site
(e.g. Bistro Föhn, https://bistrofoehn.de/).

Collects the current menu photos from the page sections and returns them as an
image gallery. Old decorative photos (legacy Squarespace uploads, whose id starts
with a 13-digit timestamp) are skipped.

options (from restaurants.json):
  "sections": {"<data-url-id>": "Label", ...}   sections to include, in order
"""

import re
from datetime import date, timedelta

from bs4 import BeautifulSoup

LEGACY_ID = re.compile(r"/\d{13}-[A-Z0-9]+/")
SKIP_LABELS = {"home", "über uns", "reservierung", "unsere weine"}


def _clean(t):
    return re.sub(r"\s+", " ", (t or "").replace("\xa0", " ")).strip()


def _img_src(img):
    src = img.get("data-src") or img.get("src") or ""
    if "images.squarespace-cdn.com" not in src:
        return None
    return src.split("?")[0]


def parse(html: str, url: str = "", options=None) -> dict:
    options = options or {}
    soup = BeautifulSoup(html, "html.parser")

    nav = {}
    for a in soup.select('a[href^="/#"]'):
        sid = a["href"][2:].removesuffix("-section")
        nav.setdefault(sid, _clean(a.get_text(" ")))

    wanted = options.get("sections") or {
        sid: label for sid, label in nav.items() if label.lower() not in SKIP_LABELS
    }

    images, seen = [], set()
    for sid, label in wanted.items():
        for el in soup.select(f'[data-url-id="{sid}"]'):
            for img in el.find_all("img"):
                src = _img_src(img)
                if not src or src in seen or LEGACY_ID.search(src):
                    continue
                seen.add(src)
                images.append({
                    "src": src + "?format=1500w",
                    "thumb": src + "?format=750w",
                    "section": label,
                    "alt": _clean(img.get("alt")) or label,
                })

    today = date.today()
    start = today - timedelta(days=today.weekday())
    return {
        "kind": "images",
        "week": {"from": start.isoformat(), "to": (start + timedelta(days=6)).isoformat()},
        "notes": [],
        "days": [],
        "weekly": [],
        "images": images,
        "legend": {"allergens": {}},
    }
