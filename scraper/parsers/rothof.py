"""Parser for the weekly lunch menu (Mittagstisch) of Rothof Restaurant,
https://rothof.de/restaurant/

The menu block starts with a date range ("16.11.2026 – 20.11.2026"), followed by
a few info lines, then weekday headings each followed by the dish, and finally
"Tägliche vegetarische Alternative" with a dish served every day.
"""

import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
RANGE_RE = re.compile(r"(\d{1,2}\.\d{1,2}\.\d{4})\s*[–—-]\s*(\d{1,2}\.\d{1,2}\.\d{4})")
VEG_HEAD = re.compile(r"vegetarisch", re.I)
ALLERGEN_RE = re.compile(r"\(([A-Za-z0-9 ,]+)\)\s*$")

# keyword -> tag; only clear cases, so filters stay trustworthy
KEYWORDS = [
    ("vegan", ["vegan"]),
    ("fisch", ["fisch", "lachs", "scholle", "forelle", "zander", "garnele", "thunfisch", "dorade", "kabeljau"]),
    ("geflügel", ["hähnchen", "hühn", "huhn", "pute", "geflügel", "chicken", "ente"]),
    ("rind", ["rind", "beef", "tafelspitz"]),
    ("schwein", ["schwein", "speck", "schinken", "leberkäs", "leberkas", "spanferkel", "salami"]),
    ("fleisch", ["schnitzel", "braten", "gulasch", "burger", "wurst", "steak", "frikadelle",
                 "fleischpflanzerl", "hack", "wiener", "bolognese", "cordon bleu", "lamm", "kalb", "wild"]),
]


def _clean(t):
    return re.sub(r"\s+", " ", (t or "").replace("\xa0", " ")).strip()


def _tags(name, vegetarian):
    low = name.lower()
    if vegetarian:
        return ["vegan"] if "vegan" in low else ["vegetarisch"]
    tags = [tag for tag, words in KEYWORDS if any(w in low for w in words)]
    if "fleisch" in tags and any(t in tags for t in ("rind", "schwein", "geflügel")):
        tags.remove("fleisch")
    return tags


def _dish(text, category, vegetarian=False):
    allergens = []
    m = ALLERGEN_RE.search(text)
    if m:
        allergens = [a.strip() for a in m.group(1).split(",") if a.strip()]
        text = text[: m.start()]
    name = _clean(text)
    return {
        "category": category,
        "name": name,
        "price": None,
        "tags": _tags(name, vegetarian),
        "allergens": allergens,
    }


def parse(html: str, url: str = "", options=None) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    block = None
    for h in soup.find_all(["h2", "h3", "h4", "h5", "h6", "p"]):
        if RANGE_RE.search(h.get_text()):
            block = h.find_parent(class_="elementor-widget-container") or h.parent
            break
    if block is None:
        raise ValueError("Mittagstisch-Block nicht gefunden")

    lines = [_clean(l) for l in block.get_text("\n").split("\n")]
    lines = [l for l in lines if l]

    m = RANGE_RE.search(" ".join(lines))
    start = datetime.strptime(m.group(1), "%d.%m.%Y").date()
    end = datetime.strptime(m.group(2), "%d.%m.%Y").date()

    notes, per_day, daily = [], {}, []
    current = None  # weekday name, "VEG", or None (info lines)
    for line in lines:
        if RANGE_RE.search(line):
            continue
        if line in WEEKDAYS:
            current = line
            per_day.setdefault(current, [])
            continue
        if VEG_HEAD.search(line) and len(line) < 60 and not ALLERGEN_RE.search(line):
            current = "VEG"
            continue
        if current is None:
            notes.append(line)
        elif current == "VEG":
            daily.append(_dish(line, "Vegetarisch", vegetarian=True))
        else:
            per_day[current].append(_dish(line, "Tagesgericht"))

    days = []
    for wd in WEEKDAYS:
        if wd not in per_day:
            continue
        d = start + timedelta(days=WEEKDAYS.index(wd))
        if d > end:
            continue
        days.append({
            "date": d.isoformat(),
            "weekday": wd,
            "dishes": per_day[wd] + [dict(x) for x in daily],
        })

    return {
        "week": {"from": start.isoformat(), "to": end.isoformat()},
        "notes": notes,
        "days": days,
        "weekly": [],
        "legend": {"allergens": {}},
    }
