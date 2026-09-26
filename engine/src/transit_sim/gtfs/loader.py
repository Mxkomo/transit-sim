"""Chargement d'un GTFS et restriction à une date de référence."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from transit_sim.timeutils import parse_gtfs_time

GTFS_FILES = (
    "agency",
    "calendar",
    "calendar_dates",
    "routes",
    "shapes",
    "stops",
    "stop_times",
    "trips",
)

# Colonnes converties en nombres après lecture ; tout le reste (dont les
# identifiants) reste en chaîne de caractères.
_INT_COLUMNS = {
    "calendar": [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ],
    "calendar_dates": ["exception_type"],
    "routes": ["route_type"],
    "shapes": ["shape_pt_sequence"],
    "stops": ["location_type"],
    "stop_times": ["stop_sequence", "pickup_type", "drop_off_type"],
    "trips": ["direction_id"],
}
_FLOAT_COLUMNS = {
    "shapes": ["shape_pt_lat", "shape_pt_lon", "shape_dist_traveled"],
    "stops": ["stop_lat", "stop_lon"],
    "stop_times": ["shape_dist_traveled"],
}
_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


@dataclass
class GTFS:
    """Un DataFrame par fichier GTFS (DataFrame vide si le fichier est absent)."""

    agency: pd.DataFrame = field(default_factory=pd.DataFrame)
    calendar: pd.DataFrame = field(default_factory=pd.DataFrame)
    calendar_dates: pd.DataFrame = field(default_factory=pd.DataFrame)
    routes: pd.DataFrame = field(default_factory=pd.DataFrame)
    shapes: pd.DataFrame = field(default_factory=pd.DataFrame)
    stops: pd.DataFrame = field(default_factory=pd.DataFrame)
    stop_times: pd.DataFrame = field(default_factory=pd.DataFrame)
    trips: pd.DataFrame = field(default_factory=pd.DataFrame)


def _read_table(path: Path, name: str) -> pd.DataFrame:
    file = path / f"{name}.txt"
    if not file.exists():
        return pd.DataFrame()
    # dtype=str : aucun identifiant n'est interprété comme nombre.
    # Seules les cellules vides deviennent NaN ("NA", "null"... restent des chaînes).
    df = pd.read_csv(
        file,
        dtype=str,
        keep_default_na=False,
        na_values=[""],
        encoding="utf-8-sig",
    )
    for col in _INT_COLUMNS.get(name, []):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col]).astype("Int64")
    for col in _FLOAT_COLUMNS.get(name, []):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col]).astype("float64")
    return df


def _times_to_seconds(values: pd.Series) -> pd.Series:
    """Convertit une colonne d'horaires GTFS en secondes (Int64, NA si vide)."""
    uniques = values.dropna().unique()
    mapping = {v: parse_gtfs_time(v) for v in uniques}
    return values.map(mapping).astype("Int64")


def load_gtfs(path: str | Path) -> GTFS:
    """Charge les fichiers GTFS d'un dossier.

    Les horaires de stop_times sont convertis dans les colonnes arrival_s et
    departure_s (secondes depuis minuit).
    """
    path = Path(path)
    if not path.is_dir():
        raise FileNotFoundError(f"Dossier GTFS introuvable : {path}")
    gtfs = GTFS(**{name: _read_table(path, name) for name in GTFS_FILES})
    st = gtfs.stop_times
    if not st.empty:
        st["arrival_s"] = _times_to_seconds(st["arrival_time"])
        st["departure_s"] = _times_to_seconds(st["departure_time"])
    return gtfs


def _to_date(value: date | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Date invalide : {value!r}")


def active_service_ids(gtfs: GTFS, on: date | str) -> set[str]:
    """Service_id actifs à la date donnée (calendar + exceptions de calendar_dates)."""
    day = _to_date(on)
    yyyymmdd = day.strftime("%Y%m%d")
    active: set[str] = set()

    cal = gtfs.calendar
    if not cal.empty:
        weekday = _WEEKDAYS[day.weekday()]
        in_period = (cal["start_date"] <= yyyymmdd) & (yyyymmdd <= cal["end_date"])
        runs_today = cal[weekday] == 1
        active |= set(cal.loc[in_period & runs_today, "service_id"])

    cd = gtfs.calendar_dates
    if not cd.empty:
        today = cd[cd["date"] == yyyymmdd]
        active |= set(today.loc[today["exception_type"] == 1, "service_id"])
        active -= set(today.loc[today["exception_type"] == 2, "service_id"])

    return active


def filter_by_date(gtfs: GTFS, on: date | str) -> GTFS:
    """Restreint le GTFS aux trips circulant à la date donnée et aux objets qu'ils utilisent.

    Les stop_times dont le stop_id est absent de stops sont conservés (pour être
    signalés par la validation), de même que les trips sans shape.
    """
    services = active_service_ids(gtfs, on)

    trips = gtfs.trips[gtfs.trips["service_id"].isin(services)].copy()
    trip_ids = set(trips["trip_id"])
    stop_times = gtfs.stop_times[gtfs.stop_times["trip_id"].isin(trip_ids)].copy()

    routes = gtfs.routes[gtfs.routes["route_id"].isin(set(trips["route_id"]))].copy()

    shapes = gtfs.shapes
    if not shapes.empty and "shape_id" in trips.columns:
        shapes = shapes[shapes["shape_id"].isin(set(trips["shape_id"].dropna()))].copy()

    stops = gtfs.stops
    used = stops["stop_id"].isin(set(stop_times["stop_id"]))
    if "parent_station" in stops.columns:
        parents = set(stops.loc[used, "parent_station"].dropna())
        used |= stops["stop_id"].isin(parents)
    stops = stops[used].copy()

    calendar = gtfs.calendar
    if not calendar.empty:
        calendar = calendar[calendar["service_id"].isin(services)].copy()
    calendar_dates = gtfs.calendar_dates
    if not calendar_dates.empty:
        calendar_dates = calendar_dates[calendar_dates["service_id"].isin(services)].copy()

    return dataclasses.replace(
        gtfs,
        agency=gtfs.agency.copy(),
        calendar=calendar,
        calendar_dates=calendar_dates,
        routes=routes,
        shapes=shapes,
        stops=stops,
        stop_times=stop_times,
        trips=trips,
    )
