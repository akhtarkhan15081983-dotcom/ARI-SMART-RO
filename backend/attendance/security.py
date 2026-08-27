from math import atan2, cos, radians, sin, sqrt

OFFICE_LATITUDE = 27.149028
OFFICE_LONGITUDE = 78.045000
OFFICE_RADIUS_METERS = 50.0


def distance_from_office_meters(latitude: float, longitude: float) -> float:
    """Return straight-line great-circle distance from the configured office."""
    earth_radius_meters = 6_371_000.0

    lat1 = radians(OFFICE_LATITUDE)
    lat2 = radians(latitude)
    delta_lat = radians(latitude - OFFICE_LATITUDE)
    delta_lon = radians(longitude - OFFICE_LONGITUDE)

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius_meters * c


def is_inside_office_geofence(latitude: float, longitude: float) -> bool:
    return distance_from_office_meters(latitude, longitude) <= OFFICE_RADIUS_METERS
