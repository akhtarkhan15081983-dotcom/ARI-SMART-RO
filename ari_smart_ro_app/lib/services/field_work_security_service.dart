import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class FieldWorkSecurityService {
  Future<Map<String, String>> _headers() async {
    final token = await ApiService.getAccessToken();
    return {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    };
  }

  Future<bool> declareNoParts(int jobId, {String remarks = ''}) async {
    final response = await http
        .post(
          Uri.parse('${ApiService.baseUrl}/jobs/$jobId/no-parts/'),
          headers: await _headers(),
          body: jsonEncode({
            'confirm_no_parts': true,
            'remarks': remarks,
          }),
        )
        .timeout(const Duration(seconds: 15));
    return response.statusCode == 200;
  }
}
