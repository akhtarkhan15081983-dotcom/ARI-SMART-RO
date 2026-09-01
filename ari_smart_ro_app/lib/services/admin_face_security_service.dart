import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class AdminFaceSecurityService {
  Future<List<Map<String, dynamic>>> getEngineers() async {
    final response = await http.get(
      Uri.parse('${ApiService.baseUrl}/employees/engineers/'),
      headers: await ApiService.authHeaders(),
    );

    if (response.statusCode != 200) {
      throw Exception('Unable to load engineers');
    }

    final data = jsonDecode(response.body) as List;
    return data.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<String> setReEnrollment({
    required int employeeId,
    required bool allow,
  }) async {
    final response = await http.post(
      Uri.parse(
        '${ApiService.baseUrl}/employees/$employeeId/face-enrollment-control/',
      ),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({
        'action': allow ? 'allow_reenrollment' : 'cancel_reenrollment',
      }),
    );

    final data = response.body.isNotEmpty
        ? Map<String, dynamic>.from(jsonDecode(response.body) as Map)
        : <String, dynamic>{};

    if (response.statusCode != 200) {
      throw Exception(
        data['message']?.toString() ?? 'Unable to update enrollment permission',
      );
    }

    return data['message']?.toString() ?? 'Updated';
  }
}
