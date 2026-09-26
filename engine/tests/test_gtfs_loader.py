from datetime import date
from pathlib import Path

import pytest

from transit_sim.gtfs.loader import active_service_ids, filter_by_date, load_gtfs

FIXTURE = Path(__file__).parent / "fixtures" / "mini_gtfs"
TUESDAY = date(2026, 10, 6)


@pytest.fixture(scope="module")
def gtfs():
    return load_gtfs(FIXTURE)


def test_load_all_files(gtfs):
    assert len(gtfs.routes) == 2
    assert len(gtfs.trips) == 6
    assert len(gtfs.stop_times) == 12


def test_ids_are_strings(gtfs):
    assert list(gtfs.routes["route_id"]) == ["01", "02"]
    assert "007" in set(gtfs.stops["stop_id"])
    assert gtfs.trips.loc[gtfs.trips["trip_id"] == "T1", "block_id"].item() == "0123"
    assert set(gtfs.stop_times["stop_id"]) >= {"007", "008"}


def test_times_in_seconds(gtfs):
    st = gtfs.stop_times.set_index(["trip_id", "stop_sequence"])
    assert st.loc[("T1", 2), "arrival_s"] == 8 * 3600 + 10 * 60
    assert st.loc[("T1", 2), "departure_s"] == 8 * 3600 + 11 * 60
    assert st.loc[("T1b", 2), "arrival_s"] == 25 * 3600 + 5 * 60


def test_missing_directory():
    with pytest.raises(FileNotFoundError):
        load_gtfs(FIXTURE / "absent")


def test_active_services_on_tuesday(gtfs):
    # WEEK : normal ; WEEK_CANCEL : supprimé (type 2) ; EXTRA : ajouté (type 1) ;
    # OLD : hors période ; WEEKEND : pas le mardi.
    assert active_service_ids(gtfs, TUESDAY) == {"WEEK", "EXTRA"}


def test_active_services_accepts_string_dates(gtfs):
    assert active_service_ids(gtfs, "2026-10-06") == {"WEEK", "EXTRA"}
    assert active_service_ids(gtfs, "20261006") == {"WEEK", "EXTRA"}


def test_removal_of_service_absent_from_calendar(gtfs):
    # Mercredi : EXTRA a un exception_type=2 sans être dans calendar.
    assert active_service_ids(gtfs, date(2026, 10, 7)) == {"WEEK", "WEEK_CANCEL"}


def test_active_services_weekend_and_period(gtfs):
    assert active_service_ids(gtfs, date(2026, 10, 10)) == {"WEEKEND"}
    assert active_service_ids(gtfs, date(2026, 3, 3)) == {"OLD"}
    assert active_service_ids(gtfs, date(2026, 12, 31)) == {"WEEK", "WEEK_CANCEL"}
    assert active_service_ids(gtfs, date(2027, 2, 2)) == set()


def test_filter_by_date(gtfs):
    day = filter_by_date(gtfs, TUESDAY)
    assert set(day.trips["trip_id"]) == {"T1", "T1b", "T3"}
    assert set(day.stop_times["trip_id"]) == {"T1", "T1b", "T3"}
    assert len(day.stop_times) == 6
    assert set(day.routes["route_id"]) == {"01", "02"}
    assert set(day.shapes["shape_id"]) == {"SH1", "SH3"}
    # Quais utilisés + leurs stations parentes, rien d'autre.
    assert set(day.stops["stop_id"]) == {"007", "B1", "STA", "STB"}
    assert set(day.calendar["service_id"]) == {"WEEK"}
    assert set(day.calendar_dates["service_id"]) == {"EXTRA"}


def test_filter_keeps_only_used_routes(gtfs):
    day = filter_by_date(gtfs, date(2026, 12, 31))
    assert set(day.trips["trip_id"]) == {"T1", "T1b", "T2"}
    assert set(day.routes["route_id"]) == {"01"}
    assert set(day.stops["stop_id"]) == {"007", "008", "B1", "STA", "STB"}


def test_filter_does_not_modify_source(gtfs):
    filter_by_date(gtfs, TUESDAY)
    assert len(gtfs.trips) == 6
    assert len(gtfs.stops) == 8


def test_filter_empty_day(gtfs):
    day = filter_by_date(gtfs, date(2027, 2, 2))
    assert day.trips.empty
    assert day.stop_times.empty
    assert day.stops.empty
