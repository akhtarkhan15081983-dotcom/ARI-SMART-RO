import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('navigation works without admin current location and has browser fallback', () {
    final source = File('lib/screens/engineer/map_screen.dart').readAsStringSync();

    expect(source, contains('Future<LatLng?> _tryCurrentLocation()'));
    expect(source, contains("'destination':"));
    expect(source, contains('location.latitude'));
    expect(source, contains('location.longitude'));
    expect(source, contains('if (current != null)'));
    expect(source, contains("query['origin'] ="));
    expect(source, contains("Uri.https('www.google.com', '/maps/dir/', query)"));
    expect(source, contains('LaunchMode.externalApplication'));
    expect(source, contains('LaunchMode.platformDefault'));
    expect(source, contains("'/maps/search/'"));
  });

  test('map resolves readable employee place and auto-centers live staff', () {
    final screen = File('lib/screens/engineer/map_screen.dart').readAsStringSync();
    final service = File('lib/services/engineer_map_service.dart').readAsStringSync();

    expect(screen, contains('_hasAutoCentered'));
    expect(screen, contains("_status(row) == 'LIVE'"));
    expect(screen, contains('final target = _centroid(points);'));
    expect(screen, contains('_mapController.move(target, zoom)'));
    expect(screen, contains("label: 'Current location'"));
    expect(screen, contains("label: 'Coordinates'"));
    expect(screen, contains('_service.reverseGeocode('));
    expect(service, contains('nominatim.openstreetmap.org'));
    expect(service, contains("'display_name'"));
  });

  test('live moving map interpolates markers without changing phone GPS cadence', () {
    final screen = File('lib/screens/engineer/map_screen.dart').readAsStringSync();
    final tracking = File('lib/services/live_location_service.dart').readAsStringSync();

    expect(screen, contains("_pollInterval = Duration(seconds: 5)"));
    expect(screen, contains('_markerAnimationDuration'));
    expect(screen, contains('_animateMarkers()'));
    expect(screen, contains('Curves.easeInOut.transform(t)'));
    expect(screen, contains('_displayPositions'));
    expect(screen, contains('_animationTargets'));
    expect(screen, contains('LIVE MOVING'));
    expect(tracking, contains('Duration(seconds: 20)'));
  });

  test('live moving map keeps breadcrumb trail bearing and follow mode', () {
    final source = File('lib/screens/engineer/map_screen.dart').readAsStringSync();

    expect(source, contains('_breadcrumbs'));
    expect(source, contains('_maxBreadcrumbPoints = 45'));
    expect(source, contains('_bearingBetween'));
    expect(source, contains('Icons.navigation'));
    expect(source, contains('Follow live movement'));
    expect(source, contains('_followEmployeeKey'));
    expect(source, contains('PolylineLayer(polylines: trails)'));
  });

  test('route cards do not show loading forever when admin location is absent', () {
    final source = File('lib/screens/engineer/map_screen.dart').readAsStringSync();

    expect(source, contains('Admin location unavailable'));
    expect(source, contains('Open Navigate for route'));
    expect(source, contains('Open Navigate for ETA'));
    expect(source, isNot(contains('Loading...')));
  });

  test('device health exposes notification permission status', () {
    final source = File('lib/screens/admin/device_health_admin_screen.dart')
        .readAsStringSync();

    expect(source, contains("health['notification_permission_granted'] == true"));
    expect(source, contains("label: 'Notifications'"));
    expect(source, contains("notificationGranted ? 'GRANTED' : 'DENIED'"));
  });

  test('engineers receive one-time Android battery optimization consent prompt', () {
    final battery = File('lib/services/battery_optimization_service.dart')
        .readAsStringSync();
    final health = File('lib/services/device_health_service.dart').readAsStringSync();
    final manifest = File('android/app/src/main/AndroidManifest.xml').readAsStringSync();

    expect(battery, contains('Permission.ignoreBatteryOptimizations'));
    expect(battery, contains('requestExemptionOnce'));
    expect(battery, contains('ari_battery_optimization_prompted_v1'));
    expect(health, contains("role != 'ENGINEER'"));
    expect(health, contains('requestExemptionOnce()'));
    expect(
      manifest,
      contains('android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS'),
    );
  });
}
