import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

import 'api_service.dart';

class HrmsService {
  static const _downloads = MethodChannel('com.arismartro.app/downloads');

  Future<List<Map<String, dynamic>>> leaves() async =>
      _list('/employees/hrms/leaves/', 'leaves');

  Future<Map<String, dynamic>> dashboard() async {
    final response = await http.get(
      Uri.parse('${ApiService.baseUrl}/employees/hrms/dashboard/'),
      headers: await ApiService.authHeaders(),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<List<Map<String, dynamic>>> holidays({int? year}) async => _list(
    '/employees/hrms/holidays/${year == null ? '' : '?year=$year'}',
    'holidays',
  );

  Future<void> declareHoliday({
    required DateTime date,
    required String name,
    required String description,
  }) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/employees/hrms/holidays/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({
        'date': _date(date),
        'name': name,
        'description': description,
        'is_paid': true,
      }),
    );
    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception(_message(response));
    }
  }

  Future<List<Map<String, dynamic>>> payroll({String? month}) async {
    final suffix = month == null ? '' : '?month=$month';
    return _list('/employees/hrms/payroll/$suffix', 'payroll');
  }

  Future<List<Map<String, dynamic>>> _list(String path, String key) async {
    final response = await http.get(
      Uri.parse('${ApiService.baseUrl}$path'),
      headers: await ApiService.authHeaders(),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return (data[key] as List<dynamic>? ?? const [])
        .map((row) => Map<String, dynamic>.from(row as Map))
        .toList();
  }

  Future<void> requestLeave({
    required String type,
    required DateTime start,
    required DateTime end,
    required String reason,
  }) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/employees/hrms/leaves/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({
        'leave_type': type,
        'start_date': _date(start),
        'end_date': _date(end),
        'reason': reason,
      }),
    );
    if (response.statusCode != 201) throw Exception(_message(response));
  }

  Future<void> reviewLeave({
    required int leaveId,
    required String status,
    String note = '',
  }) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/employees/hrms/leaves/$leaveId/review/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({'status': status, 'review_note': note}),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
  }

  Future<int> generatePayroll(String month) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/employees/hrms/payroll/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({'month': month}),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    return (jsonDecode(response.body)['records'] as num?)?.toInt() ?? 0;
  }

  Future<String> downloadPayroll(String month) async {
    final response = await http
        .get(
          Uri.parse(
            '${ApiService.baseUrl}/employees/hrms/reports/payroll.xlsx?month=$month',
          ),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 60));
    if (response.statusCode != 200) throw Exception(_message(response));
    final filename = 'ARI_Salary_Register_${month.replaceAll('-', '_')}.xlsx';
    if (Platform.isAndroid) {
      final path = await _downloads.invokeMethod<String>('saveFile', {
        'filename': filename,
        'mimeType':
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'bytes': response.bodyBytes,
      });
      if (path == null || path.isEmpty) {
        throw Exception('Download location not returned.');
      }
      return path;
    }
    final directory = await getApplicationDocumentsDirectory();
    final file = File('${directory.path}/$filename');
    await file.writeAsBytes(response.bodyBytes, flush: true);
    return file.path;
  }

  static String _date(DateTime value) =>
      '${value.year}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';
  static String _message(http.Response response) {
    try {
      return (jsonDecode(response.body)['detail'] ?? 'HRMS request failed.')
          .toString();
    } catch (_) {
      return 'HRMS request failed (HTTP ${response.statusCode}).';
    }
  }
}
