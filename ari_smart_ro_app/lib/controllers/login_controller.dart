import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/login_response.dart';
import '../services/api_service.dart';

class LoginController {
  Future<bool> login({
    required String phone,
    required String password,
  }) async {
    try {
      final response = await http
          .post(
            Uri.parse("${ApiService.baseUrl}/auth/login/"),
            headers: const {
              "Content-Type": "application/json",
            },
            body: jsonEncode({
              "phone": phone,
              "password": password,
            }),
          )
          .timeout(const Duration(seconds: 20));

      if (response.statusCode != 200) {
        return false;
      }

      final data = LoginResponse.fromJson(
        jsonDecode(response.body),
      );

      await ApiService.saveLoginData(
        accessToken: data.access,
        refreshToken: data.refresh,
        role: data.user.role,
        userId: data.user.id.toString(),
      );

      return true;
    } catch (_) {
      return false;
    }
  }
}
