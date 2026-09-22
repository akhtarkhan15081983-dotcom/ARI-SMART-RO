import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;

import 'api_service.dart';
import 'live_location_service.dart';
import 'offline_job_store.dart';

class DeviceHealthService {
  const DeviceHealthService();

  static const MethodChannel _channel = MethodChannel(
    'com.arismartro.app/device_capabilities',
  );

  Future<Map<String, dynamic>> collectSnapshot() async {
    final native = await _channel.invokeMapMethod<String, dynamic>(
          'getDeviceHealth',
        ) ??
        <String, dynamic>{};
    final jobPending = await OfflineJobStore().pendingCount();
    final liveLocation = LiveLocationService();
    final locationPending = await liveLocation.pendingLocationCount();
    final tracking = await liveLocation.isTracking();

    return <String, dynamic>{
      ...native,
      'live_location_tracking': tracking,
      'pending_job_actions': jobPending,
      'pending_location_points': locationPending,
    };
  }

  Future<void> report() async {
    try {
      final response = await http
          .post(
            Uri.parse('${ApiService.baseUrl}/employees/device-health/'),
            headers: await ApiService.authHeaders(),
            body: jsonEncode(await collectSnapshot()),
          )
          .timeout(const Duration(seconds: 15));
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw Exception('Device health report failed.');
      }
    } catch (_) {
      // Health reporting must never block field work.
    }
  }

  Future<List<Map<String, dynamic>>> fetchAdminHealth() async {
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}/employees/admin/device-health/'),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) {
      throw Exception('Unable to load device health.');
    }
    final decoded = jsonDecode(response.body);
    if (decoded is! List) return <Map<String, dynamic>>[];
    return decoded
        .whereType<Map>()
        .map((row) => Map<String, dynamic>.from(row))
        .toList(growable: false);
  }
}
