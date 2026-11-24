"""Parser for the Dave B. "Weekly Specials" PDF.

The PDF contains only an image (no text layer), so it is rendered with
poppler (pdftoppm) and read with Tesseract OCR (German). Needs the system
packages `poppler-utils`, `tesseract-ocr` and `tesseract-ocr-deu`.

Layout: a date range "23.11.2026 - 27.11.2026", then dishes, each with the
German name (with the price on the right) followed by an English translation.
The specials are valid all week, so every dish is listed on every day.
"""

import csv
import io
import re
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageOps

from .rothof import _tags  # same keyword-based meat/fish detection

WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]
RANGE_RE = re.compile(r"(\d{1,2}\.\d{1,2}\.\d{4})\s*[-–—]\s*(\d{1,2}\.\d{1,2}\.\d{4})")
PRICE_RE = re.compile(r"(\d{1,2}[.,]\d{2})")
EN_WORDS = re.compile(r"\b(with|and|the|of)\b", re.I)
DE_WORDS = re.compile(r"\b(mit|und|vom|im)\b", re.I)


def _clean(t):
    t = t.replace("‘", "").replace("’", " ").replace("´", "")
    t = re.sub(r"(\w)-\s", r"\1 – ", t)          # "Suppe- mit" -> "Suppe – mit"
    t = re.sub(r"\s+", " ", t).strip(" -–")
    t = re.sub(r"\s+([,.])", r"\1", t)
    return t.replace("Jalapeno", "Jalapeño")


def _ocr_tsv(img_path, psm):
    out = subprocess.run(
        ["tesseract", str(img_path), "stdout", "-l", "deu", "--psm", str(psm), "tsv"],
        capture_output=True, text=True, check=True).stdout
    return [r for r in csv.DictReader(io.StringIO(out), delimiter="\t", quoting=csv.QUOTE_NONE)
            if (r.get("text") or "").strip()]


def parse(data, url: str = "", options=None) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "menu.pdf"
        pdf.write_bytes(data if isinstance(data, bytes) else data.encode("latin-1"))
        subprocess.run(["pdftoppm", "-r", "300", "-png", "-f", "1", "-l", "1", str(pdf), str(Path(tmp) / "p")], check=True)
        png = next(Path(tmp).glob("p*.png"))
        inv = Path(tmp) / "inv.png"
        ImageOps.invert(Image.open(png).convert("L")).save(inv)   # light text on dark -> dark on light

        lines_raw = _ocr_tsv(inv, 4)
        words_sparse = _ocr_tsv(inv, 11)

    # text lines with their vertical position
    lines = {}
    for w in lines_raw:
        key = (w["block_num"], w["par_num"], w["line_num"])
        lines.setdefault(key, []).append(w)
    lines = sorted(
        ({"top": min(int(w["top"]) for w in ws),
          "left": min(int(w["left"]) for w in ws),
          "text": " ".join(w["text"] for w in ws)} for ws in lines.values()),
        key=lambda l: l["top"])

    full = " ".join(l["text"] for l in lines)
    m = RANGE_RE.search(full)
    if not m:
        raise ValueError("Datumsbereich im PDF nicht gefunden")
    start = datetime.strptime(m.group(1), "%d.%m.%Y").date()
    end = datetime.strptime(m.group(2), "%d.%m.%Y").date()
    date_top = next(l["top"] for l in lines if RANGE_RE.search(l["text"]))

    # prices in the right-hand column, as anchors for the dishes
    width = max(int(w["left"]) + int(w["width"]) for w in words_sparse)
    prices = sorted(
        ({"top": int(w["top"]), "price": PRICE_RE.search(w["text"]).group(1).replace(".", ",") + " €"}
         for w in words_sparse
         if PRICE_RE.search(w["text"]) and int(w["left"]) > width * 0.7 and int(w["top"]) > date_top + 50),
        key=lambda p: p["top"])
    if not prices:
        raise ValueError("Keine Preise im PDF gefunden")

    body = [l for l in lines if l["top"] > date_top + 50 and l["left"] < width * 0.7]
    dishes = []
    for i, p in enumerate(prices):
        lo = p["top"] - 40
        hi = prices[i + 1]["top"] - 40 if i + 1 < len(prices) else 10 ** 9
        block = [l["text"] for l in body if lo <= l["top"] < hi]
        de, en, english = [], [], False
        for t in block:
            if not english and EN_WORDS.search(t) and not DE_WORDS.search(t):
                english = True
            (en if english else de).append(t)
        name = _clean(" ".join(de))
        if not name:
            continue
        dishes.append({
            "category": "Weekly Special",
            "name": name,
            "description": _clean(" ".join(en)),
            "price": p["price"],
            "tags": _tags(name, False),
            "allergens": [],
        })
    if not dishes:
        raise ValueError("Keine Gerichte im PDF erkannt")

    days = []
    for i, wd in enumerate(WEEKDAYS):
        d = start + timedelta(days=i)
        if d > end:
            break
        days.append({"date": d.isoformat(), "weekday": wd, "dishes": [dict(x) for x in dishes]})

    return {
        "week": {"from": start.isoformat(), "to": end.isoformat()},
        "notes": ["Weekly Specials – gelten die ganze Woche, zusätzlich zu Pizza, Pasta, Salat und Green Grill",
                  "Automatisch per Texterkennung aus dem PDF gelesen – im Zweifel gilt das Original (Link „Website“)"],
        "days": days,
        "weekly": [],
        "legend": {"allergens": {}},
    }
