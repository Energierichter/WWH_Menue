# Mittagstisch 🍽️

Statische Website (GitHub Pages), die Speisepläne jeden Werktag um 10:00 Uhr (München) automatisch abruft (bis einschließlich 23.12.2026, einstellbar über `LAST_DAY` im Workflow),
archiviert und schön darstellt – mit Restaurant-Picker, Ansicht für heute + die nächsten 2 Werktage,
Filtern (vegan, ohne Fleisch, ohne Schwein) und „🎲 Was ess ich heute?".

Aktuell enthalten:

Alle Restaurants am Rosenkavalierplatz, München:

| Restaurant | Art | Quelle |
|---|---|---|
| Umweltkantine – Casino StMUV (Nr. 2) | Speiseplan, automatisch ausgelesen | https://www.stmuv.bayern.de/speiseplan/ |
| Rothof Restaurant (Denninger Str. 120) | Mittagstisch, automatisch ausgelesen | https://rothof.de/restaurant/ |
| BayWa-Kantine (Arabellastraße 4) | Tagesplan der ganzen Woche, automatisch von GenussZeit | https://baywa.sgo.genusszeit.com/menu.html |
| Bistro Föhn (Nr. 12) | Fotokarte, automatisch übernommen | https://bistrofoehn.de/ |
| Cedar Lounge (Nr. 12) | Feste Mittagskarte (Foto vom 24.11.2026, `menus/cedar-lounge.json`) | https://www.cedar-lounge.de/ |
| Namaste (Nr. 12) | Nur Infos & Links (keine eigene Website) | OpenTable |
| farry coffee grill bar (Nr. 15) | Nur Infos & Links | https://farry.eu/ |
| AMAL Café (Nr. 14) | Feste Karte (Foto vom 24.11.2026, `menus/amal.json`) | https://amal-cafe.de/ |
| Subway (Nr. 8) | Nur Infos & Links (bundesweit einheitliche Karte) | https://restaurants.subway.com/ |
| 030 Kebap (Arabellastraße 19) | Feste Karte (Flyer-Foto vom 24.11.2026, `menus/030-kebap.json`) | Instagram @030.kebap |
| Jiao Kitchen (Arabellastraße 19) | Feste Karte (Foto vom 24.11.2026, `menus/jiao-kitchen.json`) | Wolt |
| Dave B. Taste Five (Arabellapark) | Nur Infos & Foto (der PDF-Wochenplan auf dave-b.com gilt für Berlin; Parser `daveb_pdf` bleibt für später) | – |
| Paulaner's Wirtshaus (Arabellastraße 6, Westin Grand) | Business Lunch, automatisch aus dem Wochen-PDF (Link aus Kalenderwoche gebildet) | https://www.marriott.com/de/hotels/mucwi-the-westin-grand-munich/dining/ |
| L'Osteria Bogenhausen (Richard-Strauss-Str. 82) | Mittagsangebot „Il Pranzo“, automatisch von losteria.net | https://losteria.net/de/speisekarte/mittagsangebot/ |
| Pizza e Pasta Da Francesco (Richard-Strauss-Str. 56) | Feste Karte (nach Fotos, Stand Juli 2026, `menus/da-francesco.json`) | – |
| Hans im Glück (Arabellastraße 17) | Burger/Salate/Bowls automatisch von der Online-Karte (ohne Preise) | https://menu.hansimglueck-burgergrill.de/ |
| Arabellas Glühweinzauber (Nr. 4) | Weihnachtsmarkt, nur Infos – wird nach dem 23.12.2026 ausgeblendet | https://www.gluehwein-festival.de/ |

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
(die Seite zeigt nur heute und die nächsten zwei Werktage).

## Einrichtung GitHub Pages (einmalig)

1. Code auf den Branch `main` bringen (geplante Workflows laufen nur auf dem Standard-Branch).
2. Repo → **Settings → Pages → Build and deployment → Source: „GitHub Actions"**.
3. Repo → **Actions → „Speisepläne aktualisieren & veröffentlichen" → Run workflow**.

Danach ist die Seite unter `https://<user>.github.io/<repo>/` erreichbar.

## Weiteres Restaurant hinzufügen

1. Eintrag in `restaurants.json` ergänzen (`id`, `name`, `url`, `parser`, optional `cuisine`, `address`, `hours`, `phone`, `info`, `color`, `emoji`).
   Ohne auslesbaren Speiseplan: `"parser": null` – das Restaurant erscheint dann mit Infos & Links.
   Feste Karte (z. B. abfotografiert): `"parser": "static"` und die Gerichte in `menus/<id>.json` eintragen.
   Saisonal: `"until": "JJJJ-MM-TT"` blendet den Eintrag danach aus.
   Tagesaushang (z. B. Kreidetafel): `menus/<id>-heute.json` mit `"date"` – wird nur an diesem Tag angezeigt.
2. Hat die Seite ein neues Format: `scraper/parsers/<name>.py` mit `parse(html, url) -> dict`
   anlegen (Format siehe `stmuv.py`) und in `scraper/parsers/__init__.py` registrieren.
3. Lokal testen: `pip install -r scraper/requirements.txt && python scraper/scrape.py`
   und `python -m http.server` → http://localhost:8000
