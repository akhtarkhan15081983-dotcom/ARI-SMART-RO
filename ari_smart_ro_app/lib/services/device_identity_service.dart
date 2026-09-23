import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class DeviceIdentityService {
  static const _legacyAttendanceKey = 'attendance_device_id';

  static Future<String> getOrCreate() async {
    final canonical = await ApiService.canonicalDeviceId();
    final legacy = (await ApiService.storage.read(key: _legacyAttendanceKey))?.trim();

    if (legacy == null || legacy.isEmpty) {
      await ApiService.storage.write(
        key: _legacyAttendanceKey,
        value: canonical,
      );
      return canonical;
    }

    if (legacy == canonical) return canonical;

    // Same-installation upgrades may still carry an older attendance-only ID.
    // Ask the backend to migrate only when it can prove continuity. On any
    // failure, keep using the legacy attendance ID so existing attendance is
    // never broken merely because a migration call failed.
    try {
      final response = await http
          .post(
            Uri.parse('${ApiService.baseUrl}/employees/device-identity/migrate/'),
            headers: await ApiService.authHeaders(),
            body: jsonEncode(<String, String>{
              'legacy_attendance_device_id': legacy,
            }),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode >= 200 && response.statusCode < 300) {
        await ApiService.storage.write(
          key: _legacyAttendanceKey,
          value: canonical,
        );
        return canonical;
      }
    } catch (_) {
      // Preserve the proven legacy attendance identity on network/server errors.
    }

    return legacy;
  }
}
