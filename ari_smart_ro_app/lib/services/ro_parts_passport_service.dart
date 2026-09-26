import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class ROPartsPassportService {
  const ROPartsPassportService();

  Future<Map<String, String>> _headers({bool json = false}) async {
    final token = await ApiService.getAccessToken();
    return {
      'Authorization': 'Bearer $token',
      if (json) 'Content-Type': 'application/json',
    };
  }

  Future<Map<String, dynamic>> scanJob(
    int jobId,
    List<String> imagePaths,
  ) async {
    if (imagePaths.length < 3 || imagePaths.length > 4) {
      throw Exception('Take 3 or 4 RO photos.');
    }
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('${ApiService.baseUrl}/jobs/$jobId/ro-parts/scan/'),
    );
    request.headers.addAll(await _headers());
    for (final path in imagePaths) {
      request.files.add(await http.MultipartFile.fromPath('photos', path));
    }
    final streamed = await request.send().timeout(const Duration(seconds: 90));
    final response = await http.Response.fromStream(streamed);
    final body = _decode(response.body);
    if (response.statusCode != 201) {
      throw Exception(body['detail']?.toString() ?? 'RO visual scan failed.');
    }
    return body;
  }

  Future<Map<String, dynamic>> confirmInspection({
    required int jobId,
    required int inspectionId,
    required List<Map<String, dynamic>> parts,
  }) async {
    final response = await http
        .post(
          Uri.parse(
            '${ApiService.baseUrl}/jobs/$jobId/ro-parts/inspections/$inspectionId/confirm/',
          ),
          headers: await _headers(json: true),
          body: jsonEncode({'parts': parts}),
        )
        .timeout(const Duration(seconds: 30));
    final body = _decode(response.body);
    if (response.statusCode != 200) {
      throw Exception(body['detail']?.toString() ?? 'Unable to confirm RO parts.');
    }
    return body;
  }

  Future<Map<String, dynamic>> customerPassport() async {
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}/jobs/customer/ro-parts-passport/'),
          headers: await _headers(),
        )
        .timeout(const Duration(seconds: 20));
    final body = _decode(response.body);
    if (response.statusCode != 200) {
      throw Exception(body['detail']?.toString() ?? 'Unable to load RO parts passport.');
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
