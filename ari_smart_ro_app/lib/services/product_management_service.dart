import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class ProductManagementService {
  const ProductManagementService();

  Future<List<Map<String, dynamic>>> categories() async {
    final response = await http.get(
      Uri.parse('${ApiService.baseUrl}/products/categories/'),
      headers: await ApiService.authHeaders(),
    );
    return _list(response);
  }

  Future<List<Map<String, dynamic>>> products() async {
    final response = await http.get(
      Uri.parse('${ApiService.baseUrl}/products/models/'),
      headers: await ApiService.authHeaders(),
    );
    return _list(response);
  }

  Future<Map<String, dynamic>> createCategory(String name) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/products/categories/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({'name': name, 'is_active': true}),
    );
    return _object(response);
  }

  Future<Map<String, dynamic>> saveProduct({
    int? id,
    required Map<String, dynamic> data,
  }) async {
    final uri = id == null
        ? Uri.parse('${ApiService.baseUrl}/products/models/')
        : Uri.parse('${ApiService.baseUrl}/products/models/$id/');
    final headers = await ApiService.authHeaders();
    final body = jsonEncode(data);
    final response = id == null
        ? await http.post(uri, headers: headers, body: body)
        : await http.patch(uri, headers: headers, body: body);
    return _object(response);
  }

  Future<void> uploadImage(int productId, String imagePath) async {
    final token = await ApiService.getAccessToken();
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('${ApiService.baseUrl}/products/models/$productId/image/'),
    );
    if (token != null && token.isNotEmpty) {
      request.headers['Authorization'] = 'Bearer $token';
    }
    request.files.add(await http.MultipartFile.fromPath('image', imagePath));
    final response = await request.send();
    final body = await response.stream.bytesToString();
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(_message(body, response.statusCode));
    }
  }

  List<Map<String, dynamic>> _list(http.Response response) {
    if (response.statusCode != 200) {
      throw Exception(_message(response.body, response.statusCode));
    }
    final decoded = jsonDecode(response.body) as List<dynamic>;
    return decoded.cast<Map<String, dynamic>>();
  }

  Map<String, dynamic> _object(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(_message(response.body, response.statusCode));
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  String _message(String body, int statusCode) {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map<String, dynamic>) {
        return decoded.entries
            .map((entry) => '${entry.key}: ${entry.value}')
            .join('\n');
      }
    } catch (_) {}
    return 'Product request failed (HTTP $statusCode).';
  }
}
