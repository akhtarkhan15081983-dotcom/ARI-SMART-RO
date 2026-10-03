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

  test('live map summary counts and labels critical GPS gaps correctly', () {
    final source = File('lib/screens/engineer/map_screen.dart').readAsStringSync();

    expect(
      source,
      contains("status == 'MISSING' || status == 'LOCATION_MISSING'"),
    );
    expect(source, contains("final isCriticalMissing = status == 'LOCATION_MISSING';"));
    expect(source, contains("? Colors.orange"));
    expect(source, contains("? Colors.red"));
    expect(source, contains("status == 'STALE'"));
    expect(source, contains("'Checked in • GPS missing'"));
    expect(
      source,
      contains("final missing = employees.where((e) => _countsAsMissing(_status(e))).length;"),
    );
  });

  test('face reenrollment uses authenticated stable device identity', () {
    final identity = File('lib/services/device_identity_service.dart').readAsStringSync();
    final enrollment = File('lib/screens/profile/face_enrollment_screen.dart').readAsStringSync();

    expect(identity, contains('loginBoundDeviceId'));
    expect(identity, contains("headers['X-ARI-Device-ID']"));
    expect(identity, contains('static Future<void> bindTo(String deviceId)'));
    expect(enrollment, contains('DeviceIdentityService.loginBoundDeviceId()'));
    expect(enrollment, contains('await DeviceIdentityService.bindTo(deviceId);'));
    expect(
      enrollment.indexOf('await DeviceIdentityService.bindTo(deviceId);'),
      greaterThan(enrollment.indexOf('await _service.enrollFace')),
    );
  });
}
