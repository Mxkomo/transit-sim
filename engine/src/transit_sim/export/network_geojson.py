"""Export du réseau du jour en GeoJSON (lignes + stations parentes)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from transit_sim.gtfs.loader import GTFS

COORD_DECIMALS = 6


def _none_if_na(value: Any) -> Any:
    return None if pd.isna(value) else value


def _int_or_none(value: Any) -> int | None:
    return None if pd.isna(value) else int(value)


def main_shapes(gtfs: GTFS) -> pd.DataFrame:
    """Shape la plus utilisée par (route_id, direction_id) parmi les trips du GTFS.

    Colonnes : route_id, direction_id, shape_id, nb_trips (tous les trips du
    groupe, avec ou sans shape), nb_trips_shape (trips utilisant la shape retenue).
    En cas d'égalité, le shape_id le plus petit (ordre lexicographique) est retenu.
    Les groupes sans aucune shape ont shape_id = NA.
    """
    keys = ["route_id", "direction_id"]
    trips = gtfs.trips
    nb_trips = trips.groupby(keys, dropna=False).size().rename("nb_trips").reset_index()

    usage = (
        trips.dropna(subset=["shape_id"])
        .groupby([*keys, "shape_id"], dropna=False)
        .size()
        .rename("nb_trips_shape")
        .reset_index()
        .sort_values([*keys, "nb_trips_shape", "shape_id"], ascending=[True, True, False, True])
        .drop_duplicates(subset=keys, keep="first")
    )
    return nb_trips.merge(usage, on=keys, how="left")


def build_network_geojson(gtfs: GTFS) -> tuple[dict[str, Any], list[str]]:
    """Construit la FeatureCollection et la liste des avertissements rencontrés."""
    warnings: list[str] = []
    features: list[dict[str, Any]] = []

    routes = gtfs.routes.set_index("route_id")
    shapes = gtfs.shapes.sort_values(["shape_id", "shape_pt_sequence"])
    coords_by_shape = {
        shape_id: [
            [round(lon, COORD_DECIMALS), round(lat, COORD_DECIMALS)]
            for lon, lat in zip(g["shape_pt_lon"], g["shape_pt_lat"], strict=True)
        ]
        for shape_id, g in shapes.groupby("shape_id", sort=False)
    }

    for row in main_shapes(gtfs).itertuples(index=False):
        label = f"route_id={row.route_id} direction_id={_int_or_none(row.direction_id)}"
        if pd.isna(row.shape_id):
            warnings.append(f"{label} : aucun trip avec shape_id, ligne non exportée")
            continue
        coords = coords_by_shape.get(row.shape_id)
        if not coords:
            warnings.append(f"{label} : shape {row.shape_id} absente de shapes, non exportée")
            continue
        if row.route_id not in routes.index:
            warnings.append(f"{label} : route_id absent de routes, non exportée")
            continue
        route = routes.loc[row.route_id]
        color = _none_if_na(route.get("route_color"))
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {
                    "route_id": row.route_id,
                    "route_short_name": _none_if_na(route.get("route_short_name")),
                    "route_long_name": _none_if_na(route.get("route_long_name")),
                    "route_type": _int_or_none(route.get("route_type")),
                    "route_color": None if color is None else f"#{color}",
                    "direction_id": _int_or_none(row.direction_id),
                    "shape_id": row.shape_id,
                    "nb_trips_du_jour": int(row.nb_trips),
                },
            }
        )

    stops = gtfs.stops
    stations = stops[stops["location_type"] == 1] if "location_type" in stops else stops.iloc[0:0]
    for stop in stations.sort_values("stop_id").itertuples(index=False):
        if pd.isna(stop.stop_lat) or pd.isna(stop.stop_lon):
            warnings.append(f"station {stop.stop_id} sans coordonnées, non exportée")
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        round(stop.stop_lon, COORD_DECIMALS),
                        round(stop.stop_lat, COORD_DECIMALS),
                    ],
                },
                "properties": {
                    "stop_id": stop.stop_id,
                    "stop_name": _none_if_na(stop.stop_name),
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}, warnings


def write_network_geojson(gtfs: GTFS, output: str | Path) -> list[str]:
    """Écrit le GeoJSON du réseau et renvoie les avertissements."""
    collection, warnings = build_network_geojson(gtfs)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(collection, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    return warnings
