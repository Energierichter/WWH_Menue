"""Parser registry.

To support a new restaurant website:
  1. Create scraper/parsers/<name>.py with `parse(html, url, options=None) -> dict`
     returning the normalized menu structure (see stmuv.py / squarespace_images.py).
  2. Register it in PARSERS below.
  3. Add an entry to restaurants.json with "parser": "<name>" (and optional "options").

Restaurants without a machine-readable menu use "parser": null – they appear in
the picker with their profile (address, hours, links) only.
"""

from . import daveb_pdf, losteria, paulaner_pdf, rothof, squarespace_images, stmuv

PARSERS = {
    "stmuv": stmuv.parse,
    "squarespace_images": squarespace_images.parse,
    "rothof": rothof.parse,
    "daveb_pdf": daveb_pdf.parse,
    "losteria": losteria.parse,
    "paulaner_pdf": paulaner_pdf.parse,
}
