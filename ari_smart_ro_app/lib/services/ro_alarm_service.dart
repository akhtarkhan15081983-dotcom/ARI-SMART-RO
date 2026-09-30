import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class ROAlarmService {
  const ROAlarmService();

  Future<List<Map<String, dynamic>>> fetchAlarms({
    String status = '',
  }) async {
    final query = status.trim().isEmpty
        ? ''
        : '?status=${Uri.encodeQueryComponent(status.trim().toUpperCase())}';
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}/assets/ro-alarms/$query'),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return _asList(jsonDecode(response.body));
  }

  Future<List<Map<String, dynamic>>> fetchAssets() async {
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}/assets/ro-alarm-assets/'),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return _asList(jsonDecode(response.body));
  }

  Future<Map<String, dynamic>> reportAlarm({
    required int assetId,
    required String alarmType,
    required String message,
    int? observedValue,
  }) async {
    final payload = <String, dynamic>{
      'ro_asset': assetId,
      'alarm_type': alarmType,
      'message': message,
    };
    if (observedValue != null) payload['observed_value'] = observedValue;

    final response = await http
        .post(
          Uri.parse('${ApiService.baseUrl}/assets/ro-alarms/'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 201) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> updateAlarmStatus(
    int alarmId,
    String action,
  ) async {
    final response = await http
        .post(
          Uri.parse('${ApiService.baseUrl}/assets/ro-alarms/$alarmId/status/'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({'action': action}),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> refreshSystemAlarms({
    int horizonDays = 7,
  }) async {
    final response = await http
        .post(
          Uri.parse('${ApiService.baseUrl}/assets/ro-alarms/refresh/'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({'horizon_days': horizonDays}),
        )
        .timeout(const Duration(seconds: 30));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> updateAssetSettings({
    required int assetId,
    required bool monitoringEnabled,
    String? nextFilterChangeDate,
    int? outputTdsAttentionLevel,
  }) async {
    final payload = <String, dynamic>{
      'alarm_monitoring_enabled': monitoringEnabled,
      'next_filter_change_date': nextFilterChangeDate,
      'output_tds_attention_level': outputTdsAttentionLevel,
    };
    final response = await http
        .patch(
          Uri.parse(
            '${ApiService.baseUrl}/assets/ro-alarm-assets/$assetId/settings/',
          ),
          headers: await ApiService.authHeaders(),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  List<Map<String, dynamic>> _asList(dynamic decoded) {
    if (decoded is List) {
      return decoded
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList();
    }
    if (decoded is Map && decoded['results'] is List) {
      return (decoded['results'] as List)
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList();
    }
    return const [];
  }

  String _message(http.Response response) {
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map) {
        final data = Map<String, dynamic>.from(decoded);
        return (data['detail'] ?? data['message'] ?? 'Request failed.')
            .toString();
      }
    } catch (_) {
      // Fall through to HTTP status message.
    }
    return 'Request failed (HTTP ${response.statusCode}).';
  }
}
