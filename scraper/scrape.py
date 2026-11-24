#!/usr/bin/env python3
"""Fetch every restaurant in restaurants.json and write normalized JSON to data/.

Output:
  data/index.json                      list of restaurants + available weeks
  data/<id>/latest.json                most recent menu
  data/<id>/<week-start>.json          archive (one file per week)

Usage:
  python scraper/scrape.py                    # fetch live
  python scraper/scrape.py --file id=path     # parse a local HTML file (testing)
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from parsers import PARSERS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MenuTracker/1.0)"}


def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", action="append", default=[], help="id=path to local HTML")
    args = ap.parse_args()
    local = dict(f.split("=", 1) for f in args.file)

    restaurants = json.loads((ROOT / "restaurants.json").read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    index = []
    failures = 0

    for r in restaurants:
        rid = r["id"]
        out_dir = DATA / rid
        parser = r.get("parser")
        status = "ok"
        kind = None

        if not parser:
            status = "info"
        elif parser == "static":
            # feste Karte, von Hand gepflegt in menus/<id>.json (z. B. nach Foto)
            kind = "static"
            try:
                menu = json.loads((ROOT / "menus" / f"{rid}.json").read_text(encoding="utf-8"))
                menu.update({"kind": "static", "restaurant": rid})
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / "latest.json").write_text(
                    json.dumps(menu, ensure_ascii=False, indent=2), encoding="utf-8")
                n = sum(len(s["dishes"]) for s in menu["sections"])
                print(f"[{rid}] feste Karte (Stand {menu.get('asOf')}): {n} items")
            except Exception as e:
                failures += 1
                status = f"error: {e}"
                print(f"[{rid}] FAILED: {e}", file=sys.stderr)
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            if parser == "squarespace_images":
                kind = "images"
            try:
                html = Path(local[rid]).read_text(encoding="utf-8") if rid in local else fetch(r["url"])
                menu = PARSERS[parser](html, r["url"], r.get("options"))
                n = sum(len(d["dishes"]) for d in menu["days"]) + len(menu.get("images", []))
                if n == 0:
                    raise ValueError("no menu items found")
                menu["restaurant"] = rid
                menu["fetchedAt"] = now
                # optionaler Tagesaushang (von Hand, nach Foto): menus/<id>-heute.json
                daily_file = ROOT / "menus" / f"{rid}-heute.json"
                if daily_file.exists():
                    menu["daily"] = json.loads(daily_file.read_text(encoding="utf-8"))
                payload = json.dumps(menu, ensure_ascii=False, indent=2)
                (out_dir / "latest.json").write_text(payload, encoding="utf-8")
                (out_dir / f"{menu['week']['from']}.json").write_text(payload, encoding="utf-8")
                print(f"[{rid}] {menu['week']['from']} – {menu['week']['to']}: {n} items")
            except Exception as e:  # keep the previous data if a site is down
                failures += 1
                status = f"error: {e}"
                print(f"[{rid}] FAILED: {e}", file=sys.stderr)

        weeks = sorted((p.stem for p in out_dir.glob("????-??-??.json")), reverse=True) if parser and kind != "static" else []
        entry = {k: v for k, v in r.items() if k not in ("parser", "options")}
        entry.update({"weeks": weeks, "status": status, "checkedAt": now})
        if kind:
            entry["kind"] = kind
        index.append(entry)

    (DATA / "index.json").write_text(
        json.dumps({"updatedAt": now, "restaurants": index}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if failures and failures == sum(1 for r in restaurants if r.get("parser") not in (None, "static")):
        sys.exit(1)


if __name__ == "__main__":
    main()
