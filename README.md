# Mittagstisch 🍽️

Statische Website (GitHub Pages), die Speisepläne jeden Werktag um 10:00 Uhr (München) automatisch abruft,
archiviert und schön darstellt – mit Restaurant-Picker, Tages-/Wochenansicht,
Filtern (vegan, ohne Fleisch, ohne Schwein) und „🎲 Was ess ich heute?".

Aktuell enthalten:

Alle Restaurants am Rosenkavalierplatz, München:

| Restaurant | Art | Quelle |
|---|---|---|
| Casino StMUV (Nr. 2) | Speiseplan, automatisch ausgelesen | https://www.stmuv.bayern.de/speiseplan/ |
| Rothof Restaurant (Denninger Str. 120) | Mittagstisch, automatisch ausgelesen | https://rothof.de/restaurant/ |
| Bistro Föhn (Nr. 12) | Fotokarte, automatisch übernommen | https://bistrofoehn.de/ |
| Cedar Lounge (Nr. 12) | Nur Infos & Links (Website mit Bot-Schutz) | https://www.cedar-lounge.de/ |
| Namaste (Nr. 12) | Nur Infos & Links (keine eigene Website) | OpenTable |
| farry coffee grill bar (Nr. 15) | Nur Infos & Links | https://farry.eu/ |
| AMAL Café (Nr. 14) | Nur Infos & Links | https://amal-cafe.de/ |

## So funktioniert's

```
restaurants.json          Liste der Restaurants (Name, Adresse, URL, Parser, Farbe …)
scraper/scrape.py         lädt alle Seiten, schreibt data/<id>/latest.json + Wochen-Archiv
scraper/parsers/*.py      ein Parser pro Website-Format
data/                     erzeugte JSON-Daten (werden vom Workflow committet)
index.html, assets/       die Website
.github/workflows/        GitHub Action: täglich scrapen → committen → auf Pages deployen
```

Browser dürfen fremde Seiten nicht direkt abrufen (CORS). Deshalb läuft der Scraper
jeden Werktag um 10:00 Uhr als GitHub Action, speichert die Daten als JSON im Repo, und die
Website liest nur diese JSON-Dateien. Jede Woche bleibt als Archiv erhalten
(Auswahl „Woche" auf der Seite).

## Einrichtung GitHub Pages (einmalig)

1. Code auf den Branch `main` bringen (geplante Workflows laufen nur auf dem Standard-Branch).
2. Repo → **Settings → Pages → Build and deployment → Source: „GitHub Actions"**.
3. Repo → **Actions → „Speisepläne aktualisieren & veröffentlichen" → Run workflow**.

Danach ist die Seite unter `https://<user>.github.io/<repo>/` erreichbar.

## Weiteres Restaurant hinzufügen

1. Eintrag in `restaurants.json` ergänzen (`id`, `name`, `url`, `parser`, optional `cuisine`, `address`, `hours`, `phone`, `info`, `color`, `emoji`).
   Ohne auslesbaren Speiseplan: `"parser": null` – das Restaurant erscheint dann mit Infos & Links.
2. Hat die Seite ein neues Format: `scraper/parsers/<name>.py` mit `parse(html, url) -> dict`
   anlegen (Format siehe `stmuv.py`) und in `scraper/parsers/__init__.py` registrieren.
3. Lokal testen: `pip install -r scraper/requirements.txt && python scraper/scrape.py`
   und `python -m http.server` → http://localhost:8000
