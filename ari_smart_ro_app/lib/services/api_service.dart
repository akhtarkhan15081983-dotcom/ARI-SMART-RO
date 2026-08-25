import 'package:flutter/foundation.dart';
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

  static Future<void> logout() async {
    await storage.deleteAll();
  }
}
