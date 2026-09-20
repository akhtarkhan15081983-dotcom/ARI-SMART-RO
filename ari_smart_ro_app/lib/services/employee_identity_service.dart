import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class EmployeeIdentityService {
  const EmployeeIdentityService();

  Future<Map<String, dynamic>> myIdCard() async {
    final response = await http.get(
      Uri.parse('${ApiService.baseUrl}/employees/id-card/'),
      headers: await ApiService.authHeaders(),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> verify(String code) async {
    final response = await http.get(
      Uri.parse('${ApiService.baseUrl}/employees/verify-id/$code/'),
      headers: await ApiService.authHeaders(),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  String _message(http.Response response) {
    try {
      final data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
      return (data['detail'] ?? 'Employee identity request failed.').toString();
    } catch (_) {
      return 'Employee identity request failed (HTTP ${response.statusCode}).';
    }
  }
}
