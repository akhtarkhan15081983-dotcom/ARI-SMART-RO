import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/login_response.dart';
import '../services/api_service.dart';

class LoginController {
  String lastError = '';

  Future<bool> login({required String phone, required String password}) async {
    final identifier = phone.trim();
    try {
      lastError = '';

      http.Response response;
      final looksLikePhone = RegExp(r'^\d{10}$').hasMatch(identifier);
      if (looksLikePhone) {
        response = await http
            .post(
              Uri.parse('${ApiService.baseUrl}/auth/login/'),
              headers: await ApiService.deviceHeaders(),
              body: jsonEncode({'phone': identifier, 'password': password}),
            )
            .timeout(const Duration(seconds: 20));

        if (response.statusCode != 200) {
          response = await _customerReferenceLogin(identifier, password);
        }
      } else {
        response = await _customerReferenceLogin(identifier, password);
      }

      if (response.statusCode != 200) {
        try {
          final data = jsonDecode(response.body) as Map<String, dynamic>;
          lastError = data['message']?.toString() ?? 'Unable to login.';
        } catch (_) {
          lastError = 'Unable to login. Please try again.';
        }
        return false;
      }

      final data = LoginResponse.fromJson(jsonDecode(response.body));
      await ApiService.saveLoginData(
        accessToken: data.access,
        refreshToken: data.refresh,
        role: data.user.role,
        userId: data.user.id.toString(),
      );
      return true;
    } catch (_) {
      lastError = 'Server connection failed. Check your internet and try again.';
      return false;
    }
  }

  Future<http.Response> _customerReferenceLogin(
    String identifier,
    String password,
  ) {
    return http
        .post(
          Uri.parse('${ApiService.baseUrl}/auth/existing-customer/login/'),
          headers: ApiService.deviceHeaders(),
          body: jsonEncode({'identifier': identifier, 'password': password}),
        )
        .timeout(const Duration(seconds: 20));
  }
}
