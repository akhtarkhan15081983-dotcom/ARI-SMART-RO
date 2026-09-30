import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class AdminROPassportService {
  const AdminROPassportService();

  Future<Map<String, dynamic>> fetchRegistry({String query = ''}) async {
    final uri = Uri.parse(
      '${ApiService.baseUrl}/jobs/admin/ro-parts-passports/',
    ).replace(
      queryParameters: query.trim().isEmpty ? null : {'q': query.trim()},
    );
    final response = await http
        .get(uri, headers: await ApiService.authHeaders())
        .timeout(const Duration(seconds: 25));
    final body = _decode(response.body);
    if (response.statusCode != 200) {
      throw Exception(
        body['detail']?.toString() ?? 'Unable to load Digital RO registry.',
      );
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
