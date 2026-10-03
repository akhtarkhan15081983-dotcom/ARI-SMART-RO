import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('app paints before telemetry initialization', () {
    final source = File('lib/main.dart').readAsStringSync();
    final runAppIndex = source.indexOf('runApp(const AriSmartROApp());');
    final postHogIndex = source.indexOf('unawaited(PostHogService.initialize());');

    expect(runAppIndex, greaterThanOrEqualTo(0));
    expect(postHogIndex, greaterThan(runAppIndex));
    expect(source, isNot(contains('await PostHogService.initialize();')));
  });

  test('refresh-token race does not force logout', () {
    final source = File('lib/services/api_service.dart').readAsStringSync();

    expect(source, contains('allowRotatedTokenRecovery'));
    expect(source, contains('rotatedRefresh != refresh'));
    expect(source, contains('for (var attempt = 0; attempt < 4; attempt++)'));

    final refreshMethodStart = source.indexOf('static Future<bool> _refreshAccessToken(');
    final restoreSessionStart = source.indexOf('static Future<bool> restoreSession()');
    expect(refreshMethodStart, greaterThanOrEqualTo(0));
    expect(restoreSessionStart, greaterThan(refreshMethodStart));

    final refreshBody = source.substring(refreshMethodStart, restoreSessionStart);
    expect(refreshBody, isNot(contains('await logout();')));
  });

  test('background isolate reuses the login-bound Android device identity', () {
    final source = File('lib/services/api_service.dart').readAsStringSync();

    expect(source, contains('ari_stable_android_device_id_v1'));
    expect(source, contains("final stableId = 'android-\$clean';"));
    expect(source, contains('await storage.write('));
    expect(source, contains('key: _stableAndroidDeviceIdKey'));
    expect(source, contains('final cachedStableId = await storage.read('));
    expect(source, contains("cachedStableId.startsWith('android-')"));

    final stableMethodStart = source.indexOf('static Future<String> _stableDeviceId()');
    final hashMethodStart = source.indexOf('static String _fnv1a64(');
    expect(stableMethodStart, greaterThanOrEqualTo(0));
    expect(hashMethodStart, greaterThan(stableMethodStart));

    final stableMethod = source.substring(stableMethodStart, hashMethodStart);
    final cachedIndex = stableMethod.indexOf('final cachedStableId');
    final randomFallbackIndex = stableMethod.lastIndexOf('return _deviceId();');
    expect(cachedIndex, greaterThanOrEqualTo(0));
    expect(randomFallbackIndex, greaterThan(cachedIndex));
  });
}
