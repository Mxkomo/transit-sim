"""Conversion des horaires GTFS ("HH:MM:SS", heures > 24 autorisées)."""

import re

_GTFS_TIME_RE = re.compile(r"^(\d+):([0-5]\d):([0-5]\d)$")


def parse_gtfs_time(value: str) -> int:
    """Convertit une heure GTFS "HH:MM:SS" en secondes depuis minuit.

    Les heures supérieures à 24 sont acceptées (service après minuit).
    Lève ValueError si l'entrée est mal formée.
    """
    if not isinstance(value, str):
        raise ValueError(f"Heure GTFS invalide : {value!r}")
    match = _GTFS_TIME_RE.match(value.strip())
    if match is None:
        raise ValueError(f"Heure GTFS invalide : {value!r}")
    hours, minutes, seconds = (int(part) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def format_gtfs_time(seconds: int) -> str:
    """Convertit des secondes depuis minuit en heure GTFS "HH:MM:SS".

    Lève ValueError si la valeur n'est pas un entier positif ou nul.
    """
    if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 0:
        raise ValueError(f"Nombre de secondes invalide : {seconds!r}")
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
