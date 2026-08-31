import 'dart:convert';
import 'package:http/http.dart' as http;
import 'api_service.dart';

class WorkPlannerService {
  Future<Map<String, dynamic>> calendar(
    DateTime month, {
    int? employeeId,
  }) async {
    final query = <String, String>{
      'month': '${month.year}-${month.month.toString().padLeft(2, '0')}',
      if (employeeId != null) 'employee_id': '$employeeId',
    };
    return _get('/work-planner/calendar/', query);
  }

  Future<Map<String, dynamic>> route(DateTime date, {int? employeeId}) async {
    final query = <String, String>{
      'date': _date(date),
      if (employeeId != null) 'employee_id': '$employeeId',
    };
    return _get('/work-planner/route/', query);
  }

  Future<void> reschedule({
    required String eventKey,
    required DateTime scheduledAt,
    int? employeeId,
    String reason = '',
  }) async {
    final response = await http
        .patch(
          Uri.parse('${ApiService.baseUrl}/work-planner/reschedule/'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({
            'event_key': eventKey,
            'scheduled_at': scheduledAt.toIso8601String(),
            ...?employeeId == null ? null : {'employee_id': employeeId},
            'reason': reason,
          }),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
  }

  Future<void> saveCustomerLocation({
    required int customerId,
    required double latitude,
    required double longitude,
    required double accuracy,
    String source = 'WORK_CALENDAR',
  }) async {
    final response = await http
        .post(
          Uri.parse(
            '${ApiService.baseUrl}/customers/$customerId/capture-location/',
          ),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({
            'latitude': latitude,
            'longitude': longitude,
            'accuracy': accuracy,
            'source': source,
          }),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
  }

  Future<Map<String, dynamic>> _get(
    String path,
    Map<String, String> query,
  ) async {
    final uri = Uri.parse(
      '${ApiService.baseUrl}$path',
    ).replace(queryParameters: query);
    final response = await http
        .get(uri, headers: await ApiService.authHeaders())
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  String _message(http.Response response) {
    try {
      final data = jsonDecode(response.body) as Map;
      return data['detail']?.toString() ??
          'Request failed (${response.statusCode})';
    } catch (_) {
      return 'Request failed (${response.statusCode})';
    }
  }

  String _date(DateTime value) =>
      '${value.year}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';
}
