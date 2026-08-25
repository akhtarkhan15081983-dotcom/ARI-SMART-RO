import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiService {
  static const String _configuredBaseUrl = String.fromEnvironment(
    "API_BASE_URL",
    defaultValue: "",
  );

  static const String _developmentBaseUrl =
      "http://127.0.0.1:8000/api";

  static String get baseUrl {
    final configured = _configuredBaseUrl.trim();
    if (configured.isNotEmpty) {
      return configured.endsWith("/")
          ? configured.substring(0, configured.length - 1)
          : configured;
    }

    if (kReleaseMode) {
      throw StateError(
        "API_BASE_URL is required for a release build.",
      );
    }

    return _developmentBaseUrl;
  }

  static const FlutterSecureStorage storage =
      FlutterSecureStorage();

  static Future<String?> getAccessToken() {
    return storage.read(key: "access");
  }

  static Future<String?> getRefreshToken() {
    return storage.read(key: "refresh");
  }

  static Future<Map<String, String>> authHeaders() async {
    final token = await getAccessToken();
    final headers = <String, String>{
      "Content-Type": "application/json",
    };

    if (token != null && token.isNotEmpty) {
      headers["Authorization"] = "Bearer $token";
    }

    return headers;
  }

  static Future<String?> getRole() {
    return storage.read(key: "role");
  }

  static Future<String?> getUserId() {
    return storage.read(key: "user_id");
  }

  static Future<void> saveAccessToken(String token) {
    return storage.write(key: "access", value: token);
  }

  static Future<void> saveRefreshToken(String token) {
    return storage.write(key: "refresh", value: token);
  }

  static Future<void> saveRole(String role) {
    return storage.write(key: "role", value: role);
  }

  static Future<void> saveUserId(String userId) {
    return storage.write(key: "user_id", value: userId);
  }

  static Future<void> saveLoginData({
    required String accessToken,
    String? refreshToken,
    String? role,
    String? userId,
  }) async {
    await saveAccessToken(accessToken);

    if (refreshToken != null) {
      await saveRefreshToken(refreshToken);
    }
    if (role != null) {
      await saveRole(role);
    }
    if (userId != null) {
      await saveUserId(userId);
    }
  }

  static bool _isJwtValid(String? token) {
    if (token == null || token.isEmpty) return false;
    try {
      final segments = token.split('.');
      if (segments.length != 3) return false;
      final payload = jsonDecode(
        utf8.decode(base64Url.decode(base64Url.normalize(segments[1]))),
      ) as Map<String, dynamic>;
      final expiry = payload["exp"] as int?;
      if (expiry == null) return false;
      final now = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      return expiry > now + 30;
    } catch (_) {
      return false;
    }
  }

  static Future<bool> restoreSession() async {
    final access = await getAccessToken();
    if (_isJwtValid(access)) return true;

    final refresh = await getRefreshToken();
    if (refresh == null || refresh.isEmpty) return false;

    try {
      final response = await http
          .post(
            Uri.parse("\$baseUrl/auth/token/refresh/"),
            headers: const {"Content-Type": "application/json"},
            body: jsonEncode({"refresh": refresh}),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode != 200) {
        await logout();
        return false;
      }

      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final newAccess = data["access"] as String?;
      if (!_isJwtValid(newAccess)) {
        await logout();
        return false;
      }

      await saveAccessToken(newAccess!);
      final rotatedRefresh = data["refresh"] as String?;
      if (rotatedRefresh != null && rotatedRefresh.isNotEmpty) {
        await saveRefreshToken(rotatedRefresh);
      }
      return true;
    } catch (_) {
      return false;
    }
  }

  static Future<void> logout() async {
    await storage.deleteAll();
  }
}
