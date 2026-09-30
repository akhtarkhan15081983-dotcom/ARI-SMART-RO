import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class ComplaintAssistantService {
  const ComplaintAssistantService();

  Future<Map<String, String>> _headers({bool json = false}) async {
    return {
      ...await ApiService.authHeaders(),
      if (json) 'Content-Type': 'application/json',
    };
  }

  Future<List<Map<String, dynamic>>> symptoms() async {
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}/complaints/assistant/'),
          headers: await _headers(),
        )
        .timeout(const Duration(seconds: 20));
    final body = _decode(response.body);
    if (response.statusCode != 200) {
      throw Exception(body['detail']?.toString() ?? 'Unable to load complaint assistant.');
    }
    final values = body['symptoms'] as List<dynamic>? ?? const [];
    return values.whereType<Map>().map((item) => Map<String, dynamic>.from(item)).toList();
  }

  Future<Map<String, dynamic>> guidance(String symptom) async {
    final uri = Uri.parse('${ApiService.baseUrl}/complaints/assistant/').replace(
      queryParameters: {'symptom': symptom},
    );
    final response = await http
        .get(uri, headers: await _headers())
        .timeout(const Duration(seconds: 20));
    final body = _decode(response.body);
    if (response.statusCode != 200) {
      throw Exception(body['detail']?.toString() ?? 'Unable to load safe checks.');
    }
    return body;
  }

  Future<Map<String, dynamic>> raiseComplaint({
    required String symptom,
    required String description,
  }) async {
    final response = await http
        .post(
          Uri.parse('${ApiService.baseUrl}/complaints/assistant/'),
          headers: await _headers(json: true),
          body: jsonEncode({
            'symptom': symptom,
            'description': description.trim(),
          }),
        )
        .timeout(const Duration(seconds: 30));
    final body = _decode(response.body);
    if (response.statusCode != 201) {
      throw Exception(body['detail']?.toString() ?? 'Unable to raise complaint.');
    }
    return body;
  }

  Map<String, dynamic> _decode(String value) {
    if (value.trim().isEmpty) return <String, dynamic>{};
    final decoded = jsonDecode(value);
    return decoded is Map
        ? Map<String, dynamic>.from(decoded)
        : <String, dynamic>{};
  }
}
