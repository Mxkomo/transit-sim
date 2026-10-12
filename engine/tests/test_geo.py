import numpy as np
import pytest

from transit_sim.geo import cumulative_distances, haversine, interpolate


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


def test_cumulatives_distances_regular_spaces():
    lats = np.array([49.0, 50.0, 51.0])
    lons = np.array([0.0, 0.0, 0.0])
    # distance calculated from dcode and additioned by me
    expected = np.array([0.0, 111194.92664456, 222389.85328912])
    np.testing.assert_allclose(cumulative_distances(lats, lons), expected, rtol=1e-9)


def test_cumulatives_distances_regular_spaces_list():
    lats = [49.0, 50.0, 51.0]
    lons = [0.0, 0.0, 0.0]
    # distance calculated from dcode and additioned by me
    expected = np.array([0.0, 111194.92664456, 222389.85328912])
    np.testing.assert_allclose(cumulative_distances(lats, lons), expected, rtol=1e-9)


def test_cumulative_length():
    lats = np.array([49.0, 50.0, 51.0])
    lons = np.array([0.0, 0.0, 0.0])
    assert len(cumulative_distances(lats, lons)) == 3


def test_cumulatives_distances_float_spaces():
    lats = np.array([49.0, 49.5, 51.0])
    lons = np.array([0.0, 0.0, 0.0])
    # distance cualculated from dcode and additioned by me
    expected = np.array([0.0, 55597.46332228, 222389.85328912])
    np.testing.assert_allclose(cumulative_distances(lats, lons), expected, rtol=1e-9)


def test_cumulatives_distances_same_value_array():
    lats = np.array([49.0, 49.0, 50.0])
    lons = np.array([0.0, 0.0, 0.0])
    # distance cualculated from dcode and additioned by me
    expected = np.array([0.0, 0.0, 111194.92664456])
    np.testing.assert_allclose(cumulative_distances(lats, lons), expected, rtol=1e-9)


def test_cumulative_one_value():
    lats = np.array([49.0])
    lons = np.array([0.0])
    expected = np.array([0.0])
    np.testing.assert_allclose(cumulative_distances(lats, lons), expected, rtol=1e-9)


def test_cumulative_increasing_tabs():
    lats = np.array([49.0, 49.0, 51.0])
    lons = np.array([0.0, 0.0, 0.0])
    cumulative = cumulative_distances(lats, lons)
    assert np.all(np.diff(cumulative) >= 0)


def test_cumulative_long_distances_equator():
    # 111 194,93 × 3 = 333 584,78 m
    lats = np.array([0.0, 0.0, 0.0])
    lons = np.array([0.0, 1.0, 3.0])
    expected = np.array([0.0, 111194.92664456, 333584.77993368])
    np.testing.assert_allclose(cumulative_distances(lats, lons), expected, rtol=1e-9)
