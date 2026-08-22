import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiService {
  // ============================================================
  // API BASE URL
  // ============================================================

  static const String productionBaseUrl =
    "https://farmers-wiki-payroll-friend.trycloudflare.com/api";

  static const String developmentBaseUrl =
    "https://farmers-wiki-payroll-friend.trycloudflare.com/api";

  // ============================================================
  // SELECT BASE URL
  // ============================================================

  static String get baseUrl {
    if (kReleaseMode) {
      return productionBaseUrl;
    }

    return developmentBaseUrl;
  }

  // ============================================================
  // SECURE STORAGE
  // ============================================================

  static const FlutterSecureStorage storage =
      FlutterSecureStorage();

  // ============================================================
  // GET ACCESS TOKEN
  // ============================================================

  static Future<String?> getAccessToken() async {
    return await storage.read(
      key: "access",
    );
  }

  // ============================================================
  // GET REFRESH TOKEN
  // ============================================================

  static Future<String?> getRefreshToken() async {
    return await storage.read(
      key: "refresh",
    );
  }

  // ============================================================
  // AUTH HEADERS
  // ============================================================

  static Future<Map<String, String>> authHeaders() async {
    final token = await getAccessToken();

    return {
      "Authorization": "Bearer $token",
      "Content-Type": "application/json",
    };
  }

  // ============================================================
  // GET USER ROLE
  // ============================================================

  static Future<String?> getRole() async {
    return await storage.read(
      key: "role",
    );
  }

  // ============================================================
  // GET USER ID
  // ============================================================

  static Future<String?> getUserId() async {
    return await storage.read(
      key: "user_id",
    );
  }

  // ============================================================
  // SAVE ACCESS TOKEN
  // ============================================================

  static Future<void> saveAccessToken(
    String token,
  ) async {
    await storage.write(
      key: "access",
      value: token,
    );
  }

  // ============================================================
  // SAVE REFRESH TOKEN
  // ============================================================

  static Future<void> saveRefreshToken(
    String token,
  ) async {
    await storage.write(
      key: "refresh",
      value: token,
    );
  }

  // ============================================================
  // SAVE ROLE
  // ============================================================

  static Future<void> saveRole(
    String role,
  ) async {
    await storage.write(
      key: "role",
      value: role,
    );
  }

  // ============================================================
  // SAVE USER ID
  // ============================================================

  static Future<void> saveUserId(
    String userId,
  ) async {
    await storage.write(
      key: "user_id",
      value: userId,
    );
  }

  // ============================================================
  // SAVE LOGIN DATA
  // ============================================================

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

  // ============================================================
  // LOGOUT
  // ============================================================

  static Future<void> logout() async {
    await storage.delete(
      key: "access",
    );

    await storage.delete(
      key: "refresh",
    );

    await storage.delete(
      key: "user_id",
    );

    await storage.delete(
      key: "role",
    );
  }
}
