import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class PublicRequestService {
  const PublicRequestService();

  Future<Map<String, dynamic>> submit(Map<String, dynamic> payload) async {
    final client = http.Client();
    try {
      final response = await client
          .post(
            Uri.parse('${ApiService.baseUrl}/customers/public-requests/'),
            headers: const {'Content-Type': 'application/json'},
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 70));
      final decoded = jsonDecode(response.body);
      final data = decoded is Map<String, dynamic>
          ? decoded
          : <String, dynamic>{};
      if (response.statusCode != 201) {
        throw Exception(_errorMessage(data));
      }
      return data;
    } finally {
      client.close();
    }
  }

  String _errorMessage(Map<String, dynamic> data) {
    final message = data['message'] ?? data['detail'];
    if (message != null) return message.toString();
    for (final value in data.values) {
      if (value is List && value.isNotEmpty) return value.first.toString();
    }
    return 'Unable to submit right now. Please try again.';
  }
}
