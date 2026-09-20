import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class RolePermissionService {
  const RolePermissionService();

  Future<Map<String, dynamic>> getPermissions({String? role}) async {
    final suffix = role == null || role.isEmpty ? '' : '?role=$role';
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}/tenancy/role-permissions/$suffix'),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<void> updatePermission({
    required String role,
    required String featureKey,
    required bool isAllowed,
  }) async {
    final response = await http
        .post(
          Uri.parse('${ApiService.baseUrl}/tenancy/role-permissions/'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({
            'role': role,
            'feature_key': featureKey,
            'is_allowed': isAllowed,
          }),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
  }

  String _message(http.Response response) {
    try {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return (data['detail'] ?? data['message'] ?? 'Permission request failed.')
          .toString();
    } catch (_) {
      return 'Permission request failed (HTTP ${response.statusCode}).';
    }
  }
}
