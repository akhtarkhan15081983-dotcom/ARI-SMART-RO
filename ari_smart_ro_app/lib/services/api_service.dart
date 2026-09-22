import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../utils/jwt_utils.dart';

class AriPlatformStorage {
  const AriPlatformStorage();

  static final Map<String, String> _windowsMemory = <String, String>{};
  static const FlutterSecureStorage _secure = FlutterSecureStorage();

  Future<String?> read({required String key}) {
    if (Platform.isWindows) return Future.value(_windowsMemory[key]);
    return _secure.read(key: key);
  }

  Future<void> write({required String key, required String? value}) async {
    if (Platform.isWindows) {
      if (value == null) {
        _windowsMemory.remove(key);
      } else {
        _windowsMemory[key] = value;
      }
      return;
    }
    await _secure.write(key: key, value: value);
  }

  Future<void> delete({required String key}) async {
    if (Platform.isWindows) {
      _windowsMemory.remove(key);
      return;
    }
    await _secure.delete(key: key);
  }
}

class ApiService {
  static Future<bool>? _refreshInFlight;
  static const String _configuredBaseUrl = String.fromEnvironment(
    "API_BASE_URL",
    defaultValue: "https://ari-smart-ro-api.onrender.com/api",
  );

  static String get baseUrl {
    final configured = _configuredBaseUrl.trim();
    if (configured.isNotEmpty) {
      return configured.endsWith("/")
          ? configured.substring(0, configured.length - 1)
          : configured;
    }

    return "https://ari-smart-ro-api.onrender.com/api";
  }

  static const AriPlatformStorage storage = AriPlatformStorage();

  static Future<String?> _readAccessToken() {
    return storage.read(key: "access");
  }

  static Future<String?> getAccessToken() async {
    await ensureValidSession();
    return _readAccessToken();
  }

  static Future<String?> getRefreshToken() {
    return storage.read(key: "refresh");
  }

  static Future<Map<String, String>> deviceHeaders() async {
    final deviceId = await _deviceId();
    return <String, String>{
      "Content-Type": "application/json",
      "X-ARI-Device-ID": deviceId,
    };
  }

  static Future<Map<String, String>> authHeaders() async {
    final token = await getAccessToken();
    final headers = await deviceHeaders();

    if (token != null && token.isNotEmpty) {
      headers["Authorization"] = "Bearer $token";
    }

    return headers;
  }

  static Future<String> _deviceId() async {
    const key = "ari_device_id";
    final existing = await storage.read(key: key);
    if (existing != null && existing.isNotEmpty) return existing;
    final random = Random.secure();
    final value = List<int>.generate(
      24,
      (_) => random.nextInt(256),
    ).map((byte) => byte.toRadixString(16).padLeft(2, '0')).join();
    await storage.write(key: key, value: value);
    return value;
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

  static Future<Map<String, String>?> rememberedCredentials() async {
    final enabled = await storage.read(key: "remember_login");
    if (enabled != "true") return null;
    final phone = await storage.read(key: "remembered_phone");
    final password = await storage.read(key: "remembered_password");
    if (phone == null ||
        phone.isEmpty ||
        password == null ||
        password.isEmpty) {
      return null;
    }
    return {"phone": phone, "password": password};
  }

  static Future<void> saveRememberedCredentials({
    required String phone,
    required String password,
  }) async {
    await storage.write(key: "remember_login", value: "true");
    await storage.write(key: "remembered_phone", value: phone);
    await storage.write(key: "remembered_password", value: password);
  }

  static Future<void> clearRememberedCredentials() async {
    await storage.delete(key: "remember_login");
    await storage.delete(key: "remembered_phone");
    await storage.delete(key: "remembered_password");
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

  static Future<bool> ensureValidSession() async {
    final access = await _readAccessToken();
    if (isJwtUsable(access)) return true;

    final refresh = await getRefreshToken();
    if (refresh == null || refresh.isEmpty) return false;

    final existingRefresh = _refreshInFlight;
    if (existingRefresh != null) return existingRefresh;

    final refreshOperation = _refreshAccessToken(refresh);
    _refreshInFlight = refreshOperation;
    try {
      return await refreshOperation;
    } finally {
      if (identical(_refreshInFlight, refreshOperation)) {
        _refreshInFlight = null;
      }
    }
  }

  static Future<bool> _refreshAccessToken(String refresh) async {
    try {
      final response = await http
          .post(
            Uri.parse("$baseUrl/auth/token/refresh/"),
            headers: const {"Content-Type": "application/json"},
            body: jsonEncode({"refresh": refresh}),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode != 200) {
        if (response.statusCode == 400 || response.statusCode == 401) {
          await logout();
        }
        return false;
      }

      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final newAccess = data["access"] as String?;
      if (!isJwtUsable(newAccess, refreshBefore: Duration.zero)) {
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
      // Keep the refresh token on temporary network/server failures so the
      // session can recover automatically on the next request.
      return false;
    }
  }

  static Future<bool> restoreSession() => ensureValidSession();

  static Future<void> logout() async {
    // Preserve device identity and optional Keystore-backed remembered login.
    await storage.delete(key: "access");
    await storage.delete(key: "refresh");
    await storage.delete(key: "role");
    await storage.delete(key: "user_id");
  }
}
