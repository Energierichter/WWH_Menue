"""Parser for the (nationwide) HANS IM GLÜCK menu,
https://menu.hansimglueck-burgergrill.de/

Reads the burger, salad and bowl sections. The online menu has no prices
(they differ per restaurant), so dishes are shown without price.
Returns a fixed card ("kind": "static").
"""

import html as htmllib
import re

from .rothof import _tags

# section title on the page -> (shown title, default tags)
SECTIONS = {
    "BURGER VEGAN": ("Burger vegan", ["vegan"]),
    "BURGER VEGETARISCH": ("Burger vegetarisch", ["vegetarisch"]),
    "BURGER HÄHNCHENBRUSTFILET": ("Burger Hähnchenbrust", ["geflügel"]),
    "SMASH BURGER": ("Smash Burger", ["rind"]),
    "BURGER RINDFLEISCH": ("Burger Rindfleisch", ["rind"]),
    "SALATE": ("Salate", []),
    "BOWLS": ("Bowls", []),
}
STOP = "BEILAGEN & FINGERFOOD"
GROUP_HEADERS = {"SALATE & BOWLS", "BURGER"}
SMALL = {"&", "im", "und", "mit"}


def _lines(page):
    page = re.sub(r"(?s)<(script|style|noscript|svg)[^>]*>.*?</\1>", "", page)
    text = htmllib.unescape(re.sub(r"<[^>]+>", "\n", page))
    return [re.sub(r"\s+", " ", l.replace("​", "")).strip() for l in text.splitlines()
            if l.replace("​", "").strip()]


def _nice(name):
    words = name.lower().split()
    return " ".join(w if w in SMALL else w[:1].upper() + w[1:] for w in words)


def _is_name(l):
    letters = re.sub(r"[^A-Za-zÄÖÜäöüß]", "", l)
    return bool(letters) and letters.isupper() and len(l) <= 40


def parse(page: str, url: str = "", options=None) -> dict:
    lines = _lines(page)
    # the section titles appear in the navigation first; start after the burger intro
    try:
        start = next(i for i, l in enumerate(lines) if l.startswith("Alle Burger werden"))
    except StopIteration:
        raise ValueError("Burger-Bereich nicht gefunden")

    sections, current, i = [], None, start + 1
    while i < len(lines) and lines[i] != STOP:
        l = lines[i]
        if l in GROUP_HEADERS:          # e.g. "SALATE & BOWLS" – a group heading, not a dish
            current = None
        elif l in SECTIONS:
            title, default = SECTIONS[l]
            current = {"title": title, "dishes": [], "_default": default}
            sections.append(current)
        elif current is not None and _is_name(l):
            label, desc = None, ""
            j = i + 1
            if j < len(lines) and lines[j].lower() in ("vegan", "vegetarisch"):
                label = lines[j].lower()
                j += 1
            if j < len(lines) and not _is_name(lines[j]) and lines[j] != STOP:
                desc = lines[j]
                j += 1
            tags = [label] if label else list(dict.fromkeys(current["_default"] + _tags(desc, False)))
            if not label and not tags:
                tags = []
            current["dishes"].append({"name": _nice(l), "description": desc, "price": None,
                                      "tags": tags, "allergens": [],
                                      **({} if (label or tags) else {"unknown": True})})
            i = j
            continue
        i += 1

    for s in sections:
        s.pop("_default", None)
    sections = [s for s in sections if s["dishes"]]
    if not sections:
        raise ValueError("Keine Gerichte erkannt")
    return {
        "kind": "static",
        "source": "Speisekarte von hansimglueck-burgergrill.de (automatisch)",
        "notes": [
            "Preise und aktuelle Mittagsangebote gibt es nur vor Ort – die Online-Karte enthält keine Preise.",
            "Burger mit Pflücksalat, roten Zwiebeln, Tomaten und HANS IM GLÜCK Burgersoße; Brötchen nach Wahl (Sauerteig, Mehrkorn, Brioche oder brotlos), Bratling tauschbar.",
        ],
        "sections": sections,
    }
