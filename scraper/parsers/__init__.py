"""Parser registry.

To support a new restaurant website:
  1. Create scraper/parsers/<name>.py with a function `parse(html: str, base_url: str) -> dict`
     that returns the normalized menu structure (see stmuv.py for the format).
  2. Register it in PARSERS below.
  3. Add an entry to restaurants.json with "parser": "<name>".
"""

from . import stmuv

PARSERS = {
    "stmuv": stmuv.parse,
}
