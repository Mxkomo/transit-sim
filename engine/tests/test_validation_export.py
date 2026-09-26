import dataclasses
import json
from pathlib import Path

import pandas as pd

from transit_sim.export.network_geojson import main_shapes, write_network_geojson
from transit_sim.gtfs.loader import filter_by_date, load_gtfs
from transit_sim.gtfs.validation import format_report, validation_report

FIXTURE = Path(__file__).parent / "fixtures" / "mini_gtfs"


def _day():
    return filter_by_date(load_gtfs(FIXTURE), "2026-10-06")


def test_report_counts():
    report = validation_report(_day())
    c = report["counts"]
    assert c["routes_by_type"] == {"0 (tram)": 1, "3 (bus)": 1}
    assert c["trips"] == 3
    assert c["stops_platforms"] == 2
    assert c["stops_stations"] == 2
    assert c["shapes"] == 2
    assert c["block_ids"] == 2
    assert report["time_range"] == {"first_departure_s": 8 * 3600, "last_arrival_s": 90300}
    assert all(issue["count"] == 0 for issue in report["issues"].values())
    assert "Anomalies" in format_report(report)


def test_report_detects_anomalies():
    day = _day()
    trips = day.trips.copy()
    trips.loc[trips["trip_id"] == "T3", "shape_id"] = pd.NA
    st = day.stop_times.copy()
    # T1 : stop_sequence dupliqué ; T1b : arrivée avant le départ précédent ; T3 : arrêt inconnu.
    st.loc[st["trip_id"] == "T1", "stop_sequence"] = 1
    st.loc[(st["trip_id"] == "T1b") & (st["stop_sequence"] == 2), "arrival_s"] = 0
    st.loc[(st["trip_id"] == "T3") & (st["stop_sequence"] == 1), "stop_id"] = "ZZZ"
    issues = validation_report(dataclasses.replace(day, trips=trips, stop_times=st))["issues"]

    assert issues["trips_without_shape_id"]["examples"] == ["T3"]
    assert issues["trips_with_non_increasing_stop_sequence"]["examples"] == ["T1"]
    assert "T1b" in issues["trips_with_non_monotonic_times"]["examples"]
    assert issues["stop_times_with_unknown_stop_id"]["examples"] == ["ZZZ"]


def test_main_shapes_picks_most_used():
    shapes = main_shapes(_day()).set_index(["route_id", "direction_id"])
    assert shapes.loc[("01", 0), "shape_id"] == "SH1"
    assert shapes.loc[("01", 0), "nb_trips"] == 2
    assert shapes.loc[("02", 1), "shape_id"] == "SH3"


def test_write_network_geojson(tmp_path):
    out = tmp_path / "network.geojson"
    warnings = write_network_geojson(_day(), out)
    assert warnings == []
    features = json.loads(out.read_text(encoding="utf-8"))["features"]

    lines = [f for f in features if f["geometry"]["type"] == "LineString"]
    points = [f for f in features if f["geometry"]["type"] == "Point"]
    assert len(lines) == 2
    tram = next(f for f in lines if f["properties"]["route_id"] == "01")
    assert tram["properties"]["route_color"] == "#ff0000"
    assert tram["properties"]["nb_trips_du_jour"] == 2
    assert tram["geometry"]["coordinates"][0] == [-0.3, 49.1]
    assert {p["properties"]["stop_id"] for p in points} == {"STA", "STB"}
