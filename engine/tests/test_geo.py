import pytest

from transit_sim.geo import haversine, interpolate


def test_haversine_base():
    # test value from dcode
    assert haversine(49.152054, -0.371624, 49.157124, -0.336621) == pytest.approx(
        2607.229299491975, rel=1e-3
    )


def test_haversine_same_coordonates():
    assert haversine(49.152054, -0.371624, 49.152054, -0.371624) == 0.0


def test_haversine_deg_lat():

    # on a L = O / 360° *2 pi * R
    # alors on pose
    # L = 1 / 360 * 2 pi * 6371000
    # L = 0, 002777778 * 2pi * 6371000
    # L = 0, 017453293 * 6371000
    # L = 111194, 926644559

    assert haversine(49, 0, 50, 0) == pytest.approx(111194.926644559, rel=1e-9)


def test_haversine_symetry():
    assert haversine(49.152054, -0.371624, 49.157124, -0.336621) == haversine(
        49.157124,
        -0.336621,
        49.152054,
        -0.371624,
    )


def test_interpolate_base():
    assert interpolate(28845, 28830, 28860, 1200, 1800) == pytest.approx(1500.0, rel=1e-3)


def test_interpolate_base_2():
    assert interpolate(28845, 28800, 28920, 1200, 1800) == 1425.0


def test_interpolate_same_x1_x2():
    assert interpolate(28845, 28845, 28845, 1200, 1800) == pytest.approx(1200, rel=1e-3)


def test_interpolate_rejects_x_above_range():
    with pytest.raises(ValueError):
        interpolate(28845, 28830, 28840, 1200, 1800)


def test_interpolate_reject_x_below_range():
    with pytest.raises(ValueError):
        interpolate(28845, 28846, 28850, 1200, 1800)


def test_interpolate_x_equal_x1():
    assert interpolate(28845, 28845, 28850, 1200, 1800) == 1200


def test_interpolate_x_equal_x2():
    assert interpolate(28845, 28840, 28845, 1200, 1800) == 1800
