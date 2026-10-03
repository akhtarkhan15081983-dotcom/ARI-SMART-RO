import 'dart:math';

import 'api_service.dart';

class DeviceIdentityService {
  static const _key = 'attendance_device_id';

  /// Returns the persisted attendance identity used by already-enrolled
  /// employees. Keep this legacy value stable so an app update does not
  /// silently invalidate an existing attendance-device binding.
  static Future<String> getOrCreate() async {
    final existing = await ApiService.storage.read(key: _key);
    if (existing != null && existing.trim().isNotEmpty) return existing;

    final random = Random.secure();
    final bytes = List<int>.generate(32, (_) => random.nextInt(256));
    final id = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    await ApiService.storage.write(key: _key, value: id);
    return id;
  }

  /// Returns exactly the same stable device identity sent in authenticated
  /// API headers. Secure face enrollment requires its multipart `device_id`
  /// to match this authenticated login-device binding.
  static Future<String> loginBoundDeviceId() async {
    final headers = await ApiService.deviceHeaders();
    final deviceId = (headers['X-ARI-Device-ID'] ?? '').trim();
    if (deviceId.isEmpty) {
      throw StateError('Unable to identify this phone securely.');
    }
    return deviceId;
  }

  /// Migrates attendance to the authenticated device identity only after a
  /// successful face/device enrollment. Existing enrolled employees retain
  /// their legacy attendance ID until they explicitly re-enroll.
  static Future<void> bindTo(String deviceId) async {
    final normalized = deviceId.trim();
    if (normalized.isEmpty) {
      throw ArgumentError.value(deviceId, 'deviceId', 'Device ID is required.');
    }
    await ApiService.storage.write(key: _key, value: normalized);
  }
}
