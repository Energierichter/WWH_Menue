"""Parser for GenussZeit canteen menus (e.g. BayWa-Kantine),
https://baywa.sgo.genusszeit.com/menu.html?l=de

The page lists the whole week: one tab pane per day (id="tYYYY-MM-DD"),
each with menu entries (category, name, price, description, allergen codes
and property icons such as vegan / vegetarisch).
"""

import re
from datetime import date

from bs4 import BeautifulSoup

from .rothof import _tags

WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
SMALL = {"auf", "mit", "und", "an", "in", "im", "vom", "von", "der", "die", "das", "nach", "&", "aus", "zu", "zum", "zur"}

# from /allergens.html and /additives.html (GenussZeit)
LEGEND = {
    "a": "Glutenhaltiges Getreide", "aa": "Dinkel/Khorasan-Weizen", "ab": "Roggen", "ac": "Gerste",
    "ad": "Hafer", "ae": "Kamut", "b": "Krebstiere", "c": "Eier", "d": "Fisch", "e": "Erdnüsse",
    "f": "Soja", "g": "Milch/Laktose", "h": "Schalenfrüchte", "ha": "Mandeln", "hb": "Haselnüsse",
    "hc": "Walnüsse", "hd": "Kaschunüsse", "he": "Pecannüsse", "hf": "Paranüsse", "hg": "Pistazien",
    "hh": "Macadamianüsse", "i": "Sellerie", "j": "Senf", "k": "Sesam", "l": "Schwefeldioxid/Sulfite",
    "m": "Lupinen", "n": "Weichtiere",
    "1": "mit Farbstoff", "2": "mit Konservierungsstoff", "3": "mit Nitritpökelsalz",
    "4": "mit Antioxidationsmittel", "5": "mit Geschmacksverstärker", "6": "mit Phosphat",
    "7": "mit Süßungsmittel", "8": "geschwefelt", "9": "gewachst", "10": "geschwärzt",
    "11": "koffeinhaltig", "12": "chininhaltig", "13": "mit kakaohaltiger Fettglasur",
}


def _clean(t):
    return re.sub(r"\s+", " ", (t or "").replace("\xa0", " ")).strip()


def _nice(name):
    if not name.isupper():
        return name
    words = name.lower().split()
    out = []
    for i, w in enumerate(words):
        out.append(w if (i and w in SMALL) else w[:1].upper() + w[1:])
    return re.sub(r"-(\w)", lambda m: "-" + m.group(1).upper(), " ".join(out))


def parse(page: str, url: str = "", options=None) -> dict:
    soup = BeautifulSoup(page, "html.parser")
    days, notes = [], []
    for pane in soup.select('div.tab-pane[id^="t"]'):
        m = re.fullmatch(r"t(\d{4}-\d{2}-\d{2})", pane.get("id", ""))
        if not m:
            continue
        d = date.fromisoformat(m.group(1))
        dishes = []
        for entry in pane.select(".gz_menuentry"):
            title = _clean(entry.select_one(".gz_me_title").get_text()) if entry.select_one(".gz_me_title") else ""
            sub = entry.select_one(".gz_me_subtitle")
            if not sub:
                # info entries: soup of the day or price notes (salad bar, desserts …)
                if "€" in title:
                    if "suppe" in title.lower():
                        p = re.search(r"(\d{1,2},\d{2})", title)
                        dishes.append({"category": "Suppentopf", "name": "Tagessuppe",
                                       "description": "täglich wechselnd – bitte Hinweis an der Ausgabe beachten",
                                       "price": f"{p.group(1)} €" if p else None, "tags": [],
                                       "allergens": [], "unknown": True})
                    elif title not in notes:
                        notes.append(title)
                continue
            price_el = sub.select_one(".gz_me_price")
            price = None
            if price_el:
                pm = re.search(r"(\d{1,2},\d{2})", price_el.get_text())
                price = f"{pm.group(1)} €" if pm else None
                price_el.extract()
            name = _nice(_clean(sub.get_text()))
            desc_el = entry.select_one(".gz_me_description")
            desc = _clean(desc_el.get_text()) if desc_el else ""
            btn = entry.select_one("[data-ingridients]")
            allergens = [a for a in (btn.get("data-ingridients", "").split(",") if btn else []) if a]
            props = [img.get("title", "").lower() for img in entry.select(".gz_me_category img")]
            if "vegan" in props:
                tags = ["vegan"]
            elif "vegetarisch" in props:
                tags = ["vegetarisch"]
            else:
                tags = _tags(f"{name} {desc}", False)
            dish = {"category": title, "name": name, "description": desc, "price": price,
                    "tags": tags, "allergens": allergens}
            if not tags:
                dish["unknown"] = True     # not marked vegetarian and no clear meat/fish keyword
            dishes.append(dish)
        days.append({"date": d.isoformat(), "weekday": WEEKDAYS[d.weekday()], "dishes": dishes})

    days = [dd for dd in days if dd["dishes"]]
    if not days:
        raise ValueError("Keine Tage/Gerichte gefunden")
    days.sort(key=lambda dd: dd["date"])
    start = date.fromisoformat(days[0]["date"])
    monday = start.fromordinal(start.toordinal() - start.weekday())
    return {
        "week": {"from": monday.isoformat(), "to": days[-1]["date"]},
        "notes": notes,
        "days": days,
        "weekly": [],
        "legend": {"allergens": LEGEND},
    }
