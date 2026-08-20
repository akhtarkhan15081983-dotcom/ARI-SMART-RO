from django.test import SimpleTestCase

from .security import (
    OFFICE_LATITUDE,
    OFFICE_LONGITUDE,
    OFFICE_RADIUS_METERS,
    distance_from_office_meters,
    is_inside_office_geofence,
)


class OfficeGeofenceTests(SimpleTestCase):
    def test_office_coordinate_is_inside_geofence(self):
        self.assertTrue(
            is_inside_office_geofence(OFFICE_LATITUDE, OFFICE_LONGITUDE)
        )
        self.assertAlmostEqual(
            distance_from_office_meters(OFFICE_LATITUDE, OFFICE_LONGITUDE),
            0.0,
            places=3,
        )

    def test_point_about_40m_north_is_allowed(self):
        latitude = OFFICE_LATITUDE + (40.0 / 111_320.0)
        self.assertLess(
            distance_from_office_meters(latitude, OFFICE_LONGITUDE),
            OFFICE_RADIUS_METERS,
        )
        self.assertTrue(is_inside_office_geofence(latitude, OFFICE_LONGITUDE))

    def test_point_about_60m_north_is_rejected(self):
        latitude = OFFICE_LATITUDE + (60.0 / 111_320.0)
        self.assertGreater(
            distance_from_office_meters(latitude, OFFICE_LONGITUDE),
            OFFICE_RADIUS_METERS,
        )
        self.assertFalse(is_inside_office_geofence(latitude, OFFICE_LONGITUDE))
