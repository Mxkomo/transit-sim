"""Rapport de validation d'un GTFS (en principe déjà filtré sur une date).

Le rapport constate ; il ne corrige rien.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from transit_sim.gtfs.loader import GTFS
from transit_sim.timeutils import format_gtfs_time

ROUTE_TYPE_LABELS = {
    0: "tram",
    1: "métro",
    2: "train",
    3: "bus",
    4: "ferry",
    5: "tramway à câble",
    6: "téléphérique",
    7: "funiculaire",
    11: "trolleybus",
    12: "monorail",
}
MAX_EXAMPLES = 10


def _issue(ids: pd.Series | list | set) -> dict[str, Any]:
    ids = sorted(set(ids))
    return {"count": len(ids), "examples": ids[:MAX_EXAMPLES]}


def _non_increasing_sequences(stop_times: pd.DataFrame) -> set[str]:
    """Trips dont les stop_sequence, dans l'ordre du fichier, ne croissent pas strictement."""
    diff = stop_times.groupby("trip_id", sort=False)["stop_sequence"].diff()
    return set(stop_times.loc[diff <= 0, "trip_id"])


def _non_monotonic_times(stop_times: pd.DataFrame) -> set[str]:
    """Trips où la suite arrivée, départ, arrivée suivante... décroît à un moment.

    Les stop_times sont ordonnés par stop_sequence ; les horaires vides sont ignorés.
    """
    cols = ["trip_id", "stop_sequence", "arrival_s", "departure_s"]
    long = stop_times[cols].melt(
        id_vars=["trip_id", "stop_sequence"], var_name="kind", value_name="t"
    )
    # arrival_s avant departure_s au même arrêt
    long = long.dropna(subset=["t"]).sort_values(["trip_id", "stop_sequence", "kind"])
    diff = long.groupby("trip_id", sort=False)["t"].diff()
    return set(long.loc[diff < 0, "trip_id"])


def validation_report(gtfs: GTFS) -> dict[str, Any]:
    routes, trips, stops, st = gtfs.routes, gtfs.trips, gtfs.stops, gtfs.stop_times

    by_type = routes["route_type"].value_counts(dropna=False).sort_index()
    routes_by_type = {
        f"{int(t)} ({ROUTE_TYPE_LABELS.get(int(t), 'inconnu')})"
        if pd.notna(t)
        else "manquant": int(n)
        for t, n in by_type.items()
    }

    loc_type = stops["location_type"].fillna(0) if "location_type" in stops else None
    n_platforms = int((loc_type == 0).sum()) if loc_type is not None else len(stops)
    n_stations = int((loc_type == 1).sum()) if loc_type is not None else 0
    n_other = len(stops) - n_platforms - n_stations

    first_dep = st["departure_s"].min() if not st.empty else pd.NA
    last_arr = st["arrival_s"].max() if not st.empty else pd.NA

    known_stops = set(stops["stop_id"])
    known_shapes = set(gtfs.shapes["shape_id"]) if not gtfs.shapes.empty else set()
    shape_col = trips["shape_id"] if "shape_id" in trips else pd.Series(pd.NA, index=trips.index)
    block_col = trips["block_id"] if "block_id" in trips else pd.Series(dtype=str)

    missing_stop_rows = st[~st["stop_id"].isin(known_stops)]
    platforms = stops[loc_type == 0] if loc_type is not None else stops
    parent_col = (
        platforms["parent_station"]
        if "parent_station" in platforms
        else pd.Series(pd.NA, index=platforms.index)
    )
    orphan_platforms = platforms.loc[parent_col.isna(), "stop_id"]
    missing_parents = set(parent_col.dropna()) - known_stops
    color_col = routes["route_color"] if "route_color" in routes else pd.Series(dtype=str)

    return {
        "counts": {
            "routes_by_type": routes_by_type,
            "routes": len(routes),
            "trips": len(trips),
            "stops_platforms": n_platforms,
            "stops_stations": n_stations,
            "stops_other": n_other,
            "shapes": int(shape_col.dropna().nunique()),
            "block_ids": int(block_col.dropna().nunique()),
            "stop_times": len(st),
        },
        "time_range": {
            "first_departure_s": None if pd.isna(first_dep) else int(first_dep),
            "last_arrival_s": None if pd.isna(last_arr) else int(last_arr),
        },
        "issues": {
            "trips_without_shape_id": _issue(trips.loc[shape_col.isna(), "trip_id"]),
            "trips_with_unknown_shape_id": _issue(
                trips.loc[shape_col.notna() & ~shape_col.isin(known_shapes), "trip_id"]
            ),
            "stop_times_with_unknown_stop_id": {
                "rows": len(missing_stop_rows),
                **_issue(missing_stop_rows["stop_id"]),
            },
            "trips_with_non_increasing_stop_sequence": _issue(_non_increasing_sequences(st)),
            "trips_with_non_monotonic_times": _issue(_non_monotonic_times(st)),
            "platforms_without_parent_station": _issue(orphan_platforms),
            "unknown_parent_stations": _issue(missing_parents),
            "routes_without_color": _issue(routes.loc[color_col.isna(), "route_id"]),
        },
    }


_ISSUE_LABELS = {
    "trips_without_shape_id": "Trips sans shape_id",
    "trips_with_unknown_shape_id": "Trips dont le shape_id est absent de shapes",
    "stop_times_with_unknown_stop_id": "stop_times dont le stop_id est absent de stops",
    "trips_with_non_increasing_stop_sequence": "Trips à stop_sequence non strictement croissants",
    "trips_with_non_monotonic_times": "Trips à horaires non monotones",
    "platforms_without_parent_station": "Quais utilisés sans station parente",
    "unknown_parent_stations": "parent_station absentes de stops",
    "routes_without_color": "Lignes sans route_color",
}


def _fmt_time(seconds: int | None) -> str:
    return "—" if seconds is None else f"{format_gtfs_time(seconds)} ({seconds} s)"


def format_report(report: dict[str, Any]) -> str:
    c, t = report["counts"], report["time_range"]
    lines = ["=== Rapport de validation GTFS ===", "", "Lignes par route_type :"]
    lines += [f"  {k:<16} {v:>6}" for k, v in c["routes_by_type"].items()]
    lines += [
        f"  {'total':<16} {c['routes']:>6}",
        "",
        f"Trips               {c['trips']:>8}",
        f"stop_times          {c['stop_times']:>8}",
        f"Stops : quais       {c['stops_platforms']:>8}",
        f"        stations    {c['stops_stations']:>8}",
        f"        autres      {c['stops_other']:>8}",
        f"Shapes utilisées    {c['shapes']:>8}",
        f"block_id distincts  {c['block_ids']:>8}",
        "",
        f"Premier départ      {_fmt_time(t['first_departure_s'])}",
        f"Dernière arrivée    {_fmt_time(t['last_arrival_s'])}",
        "",
        "Anomalies :",
    ]
    for key, issue in report["issues"].items():
        label = _ISSUE_LABELS.get(key, key)
        count = issue["count"]
        extra = f" ({issue['rows']} lignes)" if "rows" in issue else ""
        status = "OK" if count == 0 else "!!"
        lines.append(f"  [{status}] {label} : {count}{extra}")
        if count:
            more = " …" if count > len(issue["examples"]) else ""
            lines.append(f"         ex. {', '.join(issue['examples'])}{more}")
    return "\n".join(lines)
