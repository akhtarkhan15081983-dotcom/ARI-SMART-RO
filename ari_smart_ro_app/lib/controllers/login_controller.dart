import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../models/login_response.dart';
import '../services/api_service.dart';

class LoginController {
  final storage = const FlutterSecureStorage();

  Future<bool> login({
    required String phone,
    required String password,
  }) async {
    try {
      print("Login Started");

      final response = await http.post(
        Uri.parse("${ApiService.baseUrl}/auth/login/"),
        headers: {
          "Content-Type": "application/json",
        },
        body: jsonEncode({
          "phone": phone,
          "password": password,
        }),
      );

      print("Status: ${response.statusCode}");
      print("Body: ${response.body}");

      if (response.statusCode == 200) {
        final data = LoginResponse.fromJson(
          jsonDecode(response.body),
        );

        await storage.write(key: "access", value: data.access);
        await storage.write(key: "refresh", value: data.refresh);
        await storage.write(
          key: "user_id",
          value: data.user.id.toString(),
        );
        await storage.write(
          key: "role",
          value: data.user.role,
        );

        return true;
      }

      return false;
    } catch (e, s) {
      print("LOGIN ERROR: $e");
      print(s);
      return false;
    }
  }
}