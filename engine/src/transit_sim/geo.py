import numpy as np

EARTH_RADIUS_M = 6371000


def haversine(lat1, long1, lat2, long2):
    """
    this function take coodonates in degrees and return the result in meter.
    Also works with numpy tabs
    """
    lat1_rad, lat2_rad = np.deg2rad(lat1), np.deg2rad(lat2)
    lat_rad_hav = np.deg2rad(lat2 - lat1) / 2
    long_rad_hav = np.deg2rad(long2 - long1) / 2
    a = np.sin(lat_rad_hav) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(long_rad_hav) ** 2
    distance = 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))

    return distance


def interpolate(x, x1, x2, y1, y2):
    """
    give an interpolation between 2 points (x1,y1) and (x2,y2) depending on x,
    return y1 if x1 = x2 and raise an errorif x is not in the wanted range [x1,x2]
    """
    if x < min(x1, x2) or x > max(x1, x2):
        raise ValueError(f"x = {x}, x1 = {x1}, x2 = {x2}")
    if x1 == x2:
        return y1
    # because of multiplication and division of float
    if x == x2:
        return y2
    return y1 + (x - x1) * ((y2 - y1) / (x2 - x1))
