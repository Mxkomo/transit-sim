import pytest

from transit_sim.timeutils import format_gtfs_time, parse_gtfs_time


def test_parse_normal():
    assert parse_gtfs_time("08:30:15") == 8 * 3600 + 30 * 60 + 15


def test_parse_single_digit_hour():
    assert parse_gtfs_time("8:30:15") == 8 * 3600 + 30 * 60 + 15


def test_parse_midnight():
    assert parse_gtfs_time("00:00:00") == 0


def test_parse_hour_above_24():
    assert parse_gtfs_time("25:10:00") == 90600


def test_format_normal():
    assert format_gtfs_time(8 * 3600 + 30 * 60 + 15) == "08:30:15"


def test_format_midnight():
    assert format_gtfs_time(0) == "00:00:00"


def test_format_hour_above_24():
    assert format_gtfs_time(90600) == "25:10:00"


@pytest.mark.parametrize("value", ["00:00:00", "07:05:09", "23:59:59", "24:00:00", "25:10:00"])
def test_round_trip_parse_format(value):
    assert format_gtfs_time(parse_gtfs_time(value)) == value


@pytest.mark.parametrize("seconds", [0, 1, 59, 3600, 86399, 86400, 90600, 100000])
def test_round_trip_format_parse(seconds):
    assert parse_gtfs_time(format_gtfs_time(seconds)) == seconds


@pytest.mark.parametrize(
    "value",
    ["", "abc", "12:00", "12:00:00:00", "12:60:00", "12:00:60", "-1:00:00", "aa:bb:cc", None, 3600],
)
def test_parse_invalid(value):
    with pytest.raises(ValueError):
        parse_gtfs_time(value)


@pytest.mark.parametrize("seconds", [-1, 1.5, "3600", None, True])
def test_format_invalid(seconds):
    with pytest.raises(ValueError):
        format_gtfs_time(seconds)
