import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiService {

 static const String baseUrl =
    "https://ons-items-ellis-soonest.trycloudflare.com/api";
  static const FlutterSecureStorage storage =
      FlutterSecureStorage();

  static Future<String?> getAccessToken() async {
    return await storage.read(key: "access");
  }

  static Future<String?> getRole() async {
    return await storage.read(key: "role");
  }

  static Future<void> saveAccessToken(String token) async {
    await storage.write(
      key: "access",
      value: token,
    );
  }

  static Future<void> logout() async {
    await storage.delete(key: "access");
    await storage.delete(key: "refresh");
    await storage.delete(key: "user_id");
    await storage.delete(key: "role");
  }

}