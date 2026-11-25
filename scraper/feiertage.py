#!/usr/bin/env python3
"""Gesetzliche Feiertage in Bayern (Stadt München).

Mariä Himmelfahrt (15.8.) gilt in München; das Augsburger Friedensfest nur
in Augsburg und ist daher nicht enthalten. Muss mit assets/app.js
(Funktion holidays) übereinstimmen.

Aufruf:  python scraper/feiertage.py 2026-12-25   -> Exitcode 0 = Feiertag, 1 = kein Feiertag
"""

import sys
from datetime import date, timedelta


def easter(year: int) -> date:
    """Ostersonntag (Gauß/Anonymous Gregorian algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def holidays(year: int) -> dict:
    e = easter(year)
    return {
        date(year, 1, 1): "Neujahr",
        date(year, 1, 6): "Heilige Drei Könige",
        e - timedelta(days=2): "Karfreitag",
        e + timedelta(days=1): "Ostermontag",
        date(year, 5, 1): "Tag der Arbeit",
        e + timedelta(days=39): "Christi Himmelfahrt",
        e + timedelta(days=50): "Pfingstmontag",
        e + timedelta(days=60): "Fronleichnam",
        date(year, 8, 15): "Mariä Himmelfahrt",
        date(year, 10, 3): "Tag der Deutschen Einheit",
        date(year, 11, 1): "Allerheiligen",
        date(year, 12, 25): "1. Weihnachtstag",
        date(year, 12, 26): "2. Weihnachtstag",
    }


def is_holiday(d: date) -> str | None:
    return holidays(d.year).get(d)


if __name__ == "__main__":
    d = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    name = is_holiday(d)
    print(f"{d}: {name or 'kein Feiertag'}")
    sys.exit(0 if name else 1)
