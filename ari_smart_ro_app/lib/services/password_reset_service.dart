import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class PasswordResetService {
  const PasswordResetService();

  Future<void> requestReset(String phone) async {
    final response = await http
        .post(
          Uri.parse('${ApiService.baseUrl}/auth/forgot-password/request/'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({'phone': phone}),
        )
        .timeout(const Duration(seconds: 20));

    if (response.statusCode != 200) {
      throw Exception(_message(response));
    }
  }

  Future<void> completeReset({
    required String phone,
    required String code,
    required String newPassword,
  }) async {
    final response = await http
        .post(
          Uri.parse('${ApiService.baseUrl}/auth/forgot-password/complete/'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({
            'phone': phone,
            'code': code,
            'new_password': newPassword,
          }),
        )
        .timeout(const Duration(seconds: 20));

    if (response.statusCode != 200) {
      throw Exception(_message(response));
    }
  }

  Future<List<Map<String, dynamic>>> pendingRequests() async {
    final response = await http
        .get(
          Uri.parse(
            '${ApiService.baseUrl}/auth/admin/password-reset-requests/',
          ),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 20));

    if (response.statusCode != 200) {
      throw Exception(_message(response));
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return (data['requests'] as List<dynamic>? ?? const [])
        .map((row) => Map<String, dynamic>.from(row as Map))
        .toList();
  }

  Future<String?> review({
    required int requestId,
    required String action,
  }) async {
    final response = await http
        .post(
          Uri.parse(
            '${ApiService.baseUrl}/auth/admin/password-reset-requests/$requestId/review/',
          ),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({'action': action}),
        )
        .timeout(const Duration(seconds: 20));

    if (response.statusCode != 200) {
      throw Exception(_message(response));
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return data['reset_code']?.toString();
  }

  String _message(http.Response response) {
    try {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return (data['message'] ?? data['detail'] ?? 'Password reset request failed.')
          .toString();
    } catch (_) {
      return 'Password reset request failed (HTTP ${response.statusCode}).';
    }
  }
}
