import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class EmployeeManagementService {
  Future<Map<String, dynamic>> list() async {
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}/employees/manage/'),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<void> create(Map<String, dynamic> payload) async {
    final response = await http
        .post(
          Uri.parse('${ApiService.baseUrl}/employees/manage/'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 30));
    if (response.statusCode != 201) throw Exception(_message(response));
  }

  String _message(http.Response response) {
    try {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return (data['message'] ?? data['detail'] ?? 'Employee request failed.')
          .toString();
    } catch (_) {
      return 'Employee request failed (HTTP ${response.statusCode}).';
    }
  }
}
