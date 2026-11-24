"""Parser for L'Osteria's nationwide lunch offer "Il Pranzo",
https://losteria.net/de/speisekarte/mittagsangebot/

Returns a fixed card ("kind": "static") with the pizza lunch menu and the
pasta/salad offer. options:
  "location": name as listed on the page (e.g. "München Richard-Strauss-Straße");
              if it is missing from the list of participating restaurants a
              warning note is added.
"""

import html as htmllib
import re

from .rothof import _tags

PRICE_RE = re.compile(r"Für\s+(\d{1,2},\d{2})\s*Euro", re.I)


def _lines(page):
    page = re.sub(r"(?s)<(script|style|noscript|svg)[^>]*>.*?</\1>", "", page)
    text = htmllib.unescape(re.sub(r"<[^>]+>", "\n", page))
    return [re.sub(r"\s+", " ", l).strip() for l in text.splitlines() if l.strip()]


def parse(page: str, url: str = "", options=None) -> dict:
    options = options or {}
    lines = _lines(page)
    start = next(i for i, l in enumerate(lines) if l.lower() == "il pranzo")
    lines = lines[start:]

    price_idx = [(i, PRICE_RE.search(l).group(1)) for i, l in enumerate(lines) if PRICE_RE.search(l)]
    if len(price_idx) < 2:
        raise ValueError("Mittagspreise nicht gefunden")
    (p1_i, pizza_price), (p2_i, pasta_price) = price_idx[0], price_idx[1]

    # pizza list between "Wahl aus:" and "+ PICCOLA ..."
    try:
        a = next(i for i in range(p1_i, p2_i) if lines[i].lower().startswith("wahl aus"))
    except StopIteration:
        raise ValueError("Pizza-Auswahl nicht gefunden")
    b = next(i for i in range(a, p2_i) if lines[i].startswith("+"))
    salad_extra = re.search(r"(\d{1,2},\d{2})\s*€", lines[b])

    pizzas, i = [], a + 1
    while i < b:
        l = lines[i]
        if l.startswith("(psst"):
            i += 1
            continue
        if not l.startswith("("):
            name = re.sub(r"^Pizza\s+", "", l)
            veg = "(vegetarisch)" in name.lower()
            name = re.sub(r"\s*\(vegetarisch\)", "", name, flags=re.I).strip().title()
            name = re.sub(r"\b(E|Al|Alla|Di|Con)\b", lambda m: m.group(1).lower(), name)
            desc = ""
            if i + 1 < b and lines[i + 1].startswith("("):
                desc = lines[i + 1].strip("()")
                i += 1
            pizzas.append({
                "name": f"Pizza {name}",
                "description": desc,
                "price": f"{pizza_price} €",
                "tags": ["vegetarisch"] if veg else _tags(f"{name} {desc}", False),
                "allergens": [],
            })
        i += 1
    if not pizzas:
        raise ValueError("Keine Pizzen erkannt")

    # pasta/salad block: description lines after the second price
    pasta_desc = " ".join(l for l in lines[p2_i + 1:p2_i + 3] if not l.lower().startswith("jetzt"))
    extra = next((l for l in lines[p2_i + 1:p2_i + 8] if "INSALATA" in l.upper()), "")

    notes = [
        f"Il Pranzo: Mo–Fr bis 15 Uhr (nicht an Feiertagen). Pizza-Menü {pizza_price} € inkl. 0,3 l Softdrink oder Saftschorle"
        + (f", kleiner gemischter Salat +{salad_extra.group(1)} €" if salad_extra else "")
        + ". Auch zwei unterschiedlich belegte Hälften sind möglich.",
    ]
    if extra:
        m = re.search(r"(\d{1,2},\d{2})\s*€", extra)
        notes.append(f"Pasta oder Salat {pasta_price} € · für {m.group(1)} € zusätzlich gibt es einen kleinen gemischten Salat und einen 0,3 l Softdrink oder eine Saftschorle dazu"
                     if m else "Pasta & Salat: " + extra.capitalize())
    loc = options.get("location")
    if loc and not any(loc in l for l in lines):
        notes.append(f"Achtung: „{loc}“ steht derzeit nicht in der Liste der teilnehmenden Restaurants.")

    return {
        "kind": "static",
        "source": "losteria.net – Mittagsangebot (automatisch)",
        "notes": notes,
        "sections": [
            {"title": f"Il Pranzo · Pizza-Menü {pizza_price} € inkl. Getränk", "dishes": pizzas},
            {"title": f"Pasta oder Salat · {pasta_price} €", "dishes": [{
                "name": "Pasta oder Salat des Tages",
                "description": pasta_desc or "Auswahl je nach Standort – aktuelle Mittagskarte vor Ort",
                "price": f"{pasta_price} €", "tags": [], "allergens": [], "unknown": True,
            }]},
        ],
    }
