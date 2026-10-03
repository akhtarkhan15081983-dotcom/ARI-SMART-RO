import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('live location V3 keeps resilient GPS fallback chain', () {
    final source = File('lib/services/live_location_service.dart').readAsStringSync();

    expect(source, contains('ensureTrackingReady'));
    expect(source, contains('LocationAccuracy.high'));
    expect(source, contains('LocationAccuracy.medium'));
    expect(source, contains('Geolocator.getLastKnownPosition()'));
    expect(source, contains('_maxLastKnownAge'));
    expect(source, contains('_maxFallbackAccuracyMeters'));
    expect(source, contains("source: 'LAST_KNOWN_FALLBACK'"));
  });

  test('foreground service starts before immediate GPS capture', () {
    final source = File('lib/services/live_location_service.dart').readAsStringSync();
    final start = source.indexOf('final started = await service.startService();');
    final capture = source.indexOf('await sendCurrentLocation();');

    expect(start, greaterThanOrEqualTo(0));
    expect(capture, greaterThan(start));
  });

  test('Android task removal does not request tracking service shutdown', () {
    final manifest = File('android/app/src/main/AndroidManifest.xml').readAsStringSync();

    expect(manifest, contains('android:foregroundServiceType="location"'));
    expect(manifest, contains('android:stopWithTask="false"'));
    expect(manifest, contains('android.permission.ACCESS_BACKGROUND_LOCATION'));
    expect(manifest, contains('android.permission.FOREGROUND_SERVICE_LOCATION'));
    expect(manifest, contains('android.permission.RECEIVE_BOOT_COMPLETED'));
  });
}
