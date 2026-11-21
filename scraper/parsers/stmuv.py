"""Parser for https://www.stmuv.bayern.de/speiseplan/

Normalized output format (shared by all parsers):
{
  "week": {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"},
  "notes": ["..."],
  "days": [
    {"date": "YYYY-MM-DD", "weekday": "Montag",
     "dishes": [{"category": "Suppe", "name": "...", "price": "1,30 €",
                 "tags": ["vegan"], "allergens": ["i", "j"]}]}
  ],
  "weekly": [{"category": "Dessert", "name": "...", "price": "2,10 €", "tags": [], "allergens": []}],
  "legend": {"allergens": {"a1": "Weizen", ...}}
}
"""

import re
from datetime import date, datetime, timedelta

from bs4 import BeautifulSoup

ICON_TAGS = {
    "vegan": "vegan",
    "huhn": "geflügel",
    "schwein": "schwein",
    "rind": "rind",
    "fisch": "fisch",
}

PRICE_RE = re.compile(r"(\d+[.,]\d{2})\s*€")
WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


def _fmt_price(p: str) -> str:
    return p.replace(".", ",") + " €"


def _split_name_price(text: str):
    """'Penne alla Bolognese 7,90 €' -> ('Penne alla Bolognese', '7,90 €')"""
    m = PRICE_RE.search(text)
    if not m:
        return text, None
    name = _clean(text[: m.start()] + text[m.end():]).rstrip(" -/")
    return name, _fmt_price(m.group(1))


def _tags_from(cell, name: str):
    tags = []
    img = cell.select_one(".menue-icon img")
    src = (img.get("src") or "") if img else ""
    for key, tag in ICON_TAGS.items():
        if key in src:
            tags.append(tag)
    lowered = name.lower()
    if "*vegan*" in lowered and "vegan" not in tags:
        tags.append("vegan")
    if "*vegetarisch*" in lowered and "vegetarisch" not in tags:
        tags.append("vegetarisch")
    return tags


def _allergens(el):
    if not el:
        return []
    return [a for a in (_clean(x) for x in el.get_text().split("/")) if a]


def _parse_week(soup):
    h2 = soup.find("h2")
    text = _clean(h2.get_text()) if h2 else ""
    m = re.search(r"(\d{2}\.\d{2}\.\d{4})\s*bis\s*(\d{2}\.\d{2}\.\d{4})", text)
    if not m:
        today = date.today()
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=4)
    f = datetime.strptime(m.group(1), "%d.%m.%Y").date()
    t = datetime.strptime(m.group(2), "%d.%m.%Y").date()
    return f, t


def parse(html: str, base_url: str = "") -> dict:
    soup = BeautifulSoup(html, "html.parser")
    start, end = _parse_week(soup)

    table = soup.find("table", id="table") or soup.find("table")
    headers = [_clean(th.get_text()) for th in table.select("thead th")][1:]

    days = []
    for i, wd in enumerate(headers):
        idx = WEEKDAYS.index(wd) if wd in WEEKDAYS else i
        days.append({
            "date": (start + timedelta(days=idx)).isoformat(),
            "weekday": wd,
            "dishes": [],
        })

    for row in table.select("tbody > tr"):
        cells = row.find_all("td", recursive=False)
        if not cells:
            continue
        head = cells[0]
        cat_el = head.select_one(".column-header")
        category = _clean(cat_el.get_text()) if cat_el else _clean(head.get_text())
        cat_price_el = head.find("span")
        cat_price = _clean(cat_price_el.get_text()) if cat_price_el else None
        if cat_price:
            cat_price = cat_price.replace(".", ",")

        for di, cell in enumerate(cells[1:]):
            if di >= len(days):
                break
            name_el = cell.select_one(".menue, .suppe")
            raw = _clean(name_el.get_text()) if name_el else ""
            if not raw:
                continue
            tags = _tags_from(cell, raw)
            name = _clean(re.sub(r"\*(vegan|vegetarisch)\*", "", raw, flags=re.I))
            name, inline_price = _split_name_price(name)
            price = inline_price
            if not price:
                # soup has its own price line inside the cell
                for span in cell.find_all("span"):
                    m = PRICE_RE.search(span.get_text())
                    if m:
                        price = _fmt_price(m.group(1))
                        break
            if not price:
                price = cat_price
            days[di]["dishes"].append({
                "category": category,
                "name": name,
                "price": price,
                "tags": tags,
                "allergens": _allergens(cell.select_one(".allergen")),
            })

    weekly = []
    for d in soup.select(".dessert"):
        txt = _clean(d.get_text())
        if not txt or txt.lower().startswith("wochendesserts"):
            continue
        name, price = _split_name_price(txt)
        parent = d.parent
        weekly.append({
            "category": "Wochendessert",
            "name": name,
            "price": price,
            "tags": [],
            "allergens": _allergens(parent.select_one(".allergen") if parent else None),
        })

    notes = []
    for h4 in soup.find_all("h4"):
        t = _clean(h4.get_text())
        if t:
            notes.append(t)

    legend = {}
    for p in soup.find_all("p"):
        t = _clean(p.get_text())
        if t.startswith("Allergene"):
            for code, label in re.findall(r"\((\w+)\)\s*=\s*([^,(]+)", t):
                legend[code] = _clean(label)

    return {
        "week": {"from": start.isoformat(), "to": end.isoformat()},
        "notes": notes,
        "days": days,
        "weekly": weekly,
        "legend": {"allergens": legend},
    }
