import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class DigitalRoService {
  const DigitalRoService();

  Future<Map<String, dynamic>> getMyRoPassport() async {
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}/customers/my-ro/'),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 25));
    final decoded = response.body.isEmpty
        ? <String, dynamic>{}
        : Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    if (response.statusCode != 200) {
      throw Exception(
        (decoded['message'] ?? decoded['detail'] ?? 'Unable to load Digital RO Passport.').toString(),
      );
    }
    return decoded;
  }

  Future<Map<String, dynamic>> getCustomerProfile() async {
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}/customers/profile/'),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 25));
    final decoded = response.body.isEmpty
        ? <String, dynamic>{}
        : Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    if (response.statusCode != 200) {
      throw Exception(
        (decoded['message'] ?? decoded['detail'] ?? 'Unable to load customer profile.').toString(),
      );
    }
    return Map<String, dynamic>.from(decoded['profile'] as Map? ?? const {});
  }
}
