import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class ExistingCustomerAccessService {
  Future<Map<String, dynamic>> start({required String identifier}) async {
    final response = await http
        .post(
          Uri.parse('${ApiService.baseUrl}/auth/existing-customer/start/'),
          headers: await ApiService.deviceHeaders(),
          body: jsonEncode({'identifier': identifier.trim()}),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> complete({
    required String activationToken,
    required String otp,
    required String newPassword,
  }) async {
    final response = await http
        .post(
          Uri.parse('${ApiService.baseUrl}/auth/existing-customer/complete/'),
          headers: await ApiService.deviceHeaders(),
          body: jsonEncode({
            'activation_token': activationToken,
            'otp': otp.trim(),
            'new_password': newPassword,
          }),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 201) throw Exception(_message(response));
    final data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    final user = Map<String, dynamic>.from(data['user'] as Map);
    await ApiService.saveLoginData(
      accessToken: data['access'].toString(),
      refreshToken: data['refresh']?.toString(),
      role: user['role']?.toString(),
      userId: user['id']?.toString(),
    );
    return data;
  }

  String _message(http.Response response) {
    try {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['message']?.toString() ?? 'Unable to continue.';
    } catch (_) {
      return 'Unable to continue. Please try again.';
    }
  }
}
