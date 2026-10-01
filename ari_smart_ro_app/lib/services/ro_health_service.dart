import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class ROHealthService {
  const ROHealthService();

  Future<Map<String, String>> _headers() async {
    final token = await ApiService.getAccessToken();
    return {'Authorization': 'Bearer $token'};
  }

  Future<Map<String, dynamic>> getHealth(String assetId) async {
    final safeAssetId = Uri.encodeComponent(assetId.trim());
    if (safeAssetId.isEmpty) {
      throw Exception('RO asset is not available.');
    }
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}/service/ro-health/$safeAssetId/'),
          headers: await _headers(),
        )
        .timeout(const Duration(seconds: 20));
    final body = _decode(response.body);
    if (response.statusCode != 200) {
      throw Exception(
        body['detail']?.toString() ?? 'Unable to load RO Health.',
      );
    }
    return body;
  }

  Map<String, dynamic> _decode(String value) {
    if (value.trim().isEmpty) return <String, dynamic>{};
    final decoded = jsonDecode(value);
    return decoded is Map
        ? Map<String, dynamic>.from(decoded)
        : <String, dynamic>{};
  }
}
