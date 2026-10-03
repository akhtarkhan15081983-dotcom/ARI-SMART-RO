import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('navigation works without admin current location', () {
    final source = File('lib/screens/engineer/map_screen.dart').readAsStringSync();

    expect(source, contains('Future<LatLng?> _tryCurrentLocation()'));
    expect(source, contains("'destination':"));
    expect(source, contains('location.latitude'));
    expect(source, contains('location.longitude'));
    expect(source, contains('if (current != null)'));
    expect(source, contains("query['origin'] ="));
    expect(source, contains("Uri.https('www.google.com', '/maps/dir/', query)"));
  });

  test('route cards do not show loading forever when admin location is absent', () {
    final source = File('lib/screens/engineer/map_screen.dart').readAsStringSync();

    expect(source, contains('Admin location unavailable'));
    expect(source, contains('Open Navigate for route'));
    expect(source, contains('Open Navigate for ETA'));
    expect(source, isNot(contains('value: routeInfo == null\n                    ? "Loading..."')));
  });

  test('device health exposes notification permission status', () {
    final source = File('lib/screens/admin/device_health_admin_screen.dart')
        .readAsStringSync();

    expect(source, contains("health['notification_permission_granted'] == true"));
    expect(source, contains("label: 'Notifications'"));
    expect(source, contains("notificationGranted ? 'GRANTED' : 'DENIED'"));
  });
}
