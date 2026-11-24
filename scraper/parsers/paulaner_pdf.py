"""Parser for the weekly "Business Lunch" PDF of Paulaner's Wirtshaus
(The Westin Grand Munich), e.g.
https://mds-assets.marriott.com/cms-platform-for-marriott/mucwi-arabellapark-dining/kw48-26-1.pdf

Page 1 is German: five weekday boxes (Montag … Freitag), a vegetarian
selection available every day, and the prices. Words are read with their
positions (pdftotext -bbox) so the columns can be separated reliably.
The week is taken from the file name (kwWW-YY).
"""

import html as htmllib
import re
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path

from .rothof import _tags

WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]
WORD_RE = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>')
CODE_RE = re.compile(r"^[A-Z]{2,}$")          # allergen codes like CDJL
PRICE_RE = re.compile(r"(\d{1,2},\d{2})\s*€")


def _words(pdf_bytes):
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "m.pdf"
        pdf.write_bytes(pdf_bytes)
        out = Path(tmp) / "b.html"
        subprocess.run(["pdftotext", "-f", "1", "-l", "1", "-bbox", str(pdf), str(out)], check=True)
        s = out.read_text(encoding="utf-8")
    return [{"x": float(a), "y": float(b), "h": float(d) - float(b), "t": htmllib.unescape(t)}
            for a, b, c, d, t in WORD_RE.findall(s)]


def _lines(words, tol=4):
    rows = []
    for w in sorted(words, key=lambda w: (w["y"], w["x"])):
        if rows and abs(rows[-1][0]["y"] - w["y"]) <= tol:
            rows[-1].append(w)
        else:
            rows.append([w])
    return [sorted(r, key=lambda w: w["x"]) for r in rows]


def _text(line):
    return " ".join(w["t"] for w in line if not CODE_RE.match(w["t"]))


def week_from_url(url):
    m = re.search(r"kw(\d{1,2})-(\d{2})", url)
    if not m:
        return None
    return date.fromisocalendar(2000 + int(m.group(2)), int(m.group(1)), 1)


def parse(data, url: str = "", options=None) -> dict:
    start = week_from_url(url)
    if not start:
        raise ValueError("Kalenderwoche nicht in der URL")
    words = _words(data)

    headers = [w for w in words if w["t"] in WEEKDAYS and w["h"] >= 15]
    if len(headers) < 3:
        raise ValueError("Wochentage im PDF nicht gefunden")
    veg_head = next((w for w in words if w["t"].startswith("Vegetarische")), None)
    choose = next((w for w in words if w["t"].startswith("Wählen")), None)
    page_w = max(w["x"] for w in words) + 50
    bottom = veg_head["y"] - 5 if veg_head else 10 ** 6

    daily = {}
    for h in headers:
        same_row_right = [o["x"] for o in headers if abs(o["y"] - h["y"]) < 10 and o["x"] > h["x"]]
        x1 = min(same_row_right) - 5 if same_row_right else page_w
        below = [o["y"] for o in headers if o["y"] > h["y"] + 30]
        y1 = min(below) - 5 if below else bottom
        box = [w for w in words if h["x"] - 5 <= w["x"] < x1 and h["y"] + 15 < w["y"] < y1
               and not CODE_RE.match(w["t"])]
        lines = [t for t in (_text(l) for l in _lines(box)) if t]
        if lines:
            daily[h["t"]] = {"category": "Tagesgericht", "name": lines[0],
                             "description": " · ".join(lines[1:]), "price": None,
                             "tags": _tags(" ".join(lines), False), "allergens": []}

    # vegetarian selection (two columns, valid every day)
    veg = []
    if veg_head and choose:
        region = [w for w in words if veg_head["y"] + 15 < w["y"] < choose["y"] - 5]
        names = [w for w in region if w["h"] >= 10]
        if names:
            # column starts = where a name segment begins (big gap to the previous word)
            starts = []
            for line in _lines(names):
                prev_end = None
                for w in line:
                    if prev_end is None or w["x"] - prev_end > 30:
                        starts.append(w["x"])
                    prev_end = w["x"] + 6 * len(w["t"])
            left = min(starts)
            right = [x for x in starts if x > left + 60]
            split = min(right) - 5 if right else page_w
            for col in (lambda w: w["x"] < split, lambda w: w["x"] >= split):
                current = None
                for line in _lines([w for w in region if col(w)]):
                    big = [w for w in line if w["h"] >= 10]
                    t = _text(line)
                    if not t:
                        continue
                    if big:
                        current = {"category": "Vegetarisch", "name": t, "description": "",
                                   "price": None, "tags": ["vegan"] if "vegan" in t.lower() else ["vegetarisch"],
                                   "allergens": []}
                        veg.append(current)
                    elif current:
                        current["description"] = (current["description"] + ", " + t).strip(", ")

    prices = []
    if choose:
        tail = " ".join(w["t"] for w in sorted([w for w in words if w["y"] > choose["y"] + 3],
                                                key=lambda w: (round(w["y"]), w["x"])))
        prices = PRICE_RE.findall(tail)
    price = " / ".join(p + " €" for p in prices[:2]) or None
    for d in list(daily.values()) + veg:
        d["price"] = price

    if not daily:
        raise ValueError("Keine Tagesgerichte erkannt")

    days = []
    for i, wd in enumerate(WEEKDAYS):
        dishes = ([daily[wd]] if wd in daily else []) + [dict(v) for v in veg]
        days.append({"date": (start + timedelta(days=i)).isoformat(), "weekday": wd, "dishes": dishes})

    notes = ["Business Lunch: täglich ein Tagesgericht oder ein Gericht aus der vegetarischen Auswahl"]
    if len(prices) >= 2:
        notes.append(f"Mit Beilagensalat {prices[0]} € · mit Beilagensalat und 0,5 l Erfrischungsgetränk {prices[1]} €")
    return {
        "week": {"from": start.isoformat(), "to": (start + timedelta(days=4)).isoformat()},
        "notes": notes,
        "days": days,
        "weekly": [],
        "legend": {"allergens": {}},
        "sourceUrl": url,
    }
