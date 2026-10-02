import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;

import 'api_service.dart';

class CorporateHrmsService {
  Future<Map<String, dynamic>> dashboard() =>
      _getMap('/employees/hrms/corporate-dashboard/');

  Future<List<Map<String, dynamic>>> directory() async {
    final data = await _getMap('/employees/hrms/directory/');
    return (data['employees'] as List<dynamic>? ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
  }

  Future<Map<String, dynamic>> employeeFile(int employeeId) =>
      _getMap('/employees/hrms/employees/$employeeId/');

  Future<Map<String, dynamic>> employeeDocuments(int employeeId) =>
      _getMap('/employees/hrms/employees/$employeeId/documents/');

  Future<Map<String, dynamic>> uploadEmployeeDocument(
    int employeeId, {
    required String documentType,
    required PlatformFile file,
    String documentNumber = '',
    String expiryDate = '',
  }) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse(
        '${ApiService.baseUrl}/employees/hrms/employees/$employeeId/documents/',
      ),
    );
    final headers = await ApiService.authHeaders();
    headers.remove('Content-Type');
    request.headers.addAll(headers);
    request.fields['document_type'] = documentType;
    if (documentNumber.trim().isNotEmpty) {
      request.fields['document_number'] = documentNumber.trim();
    }
    if (expiryDate.trim().isNotEmpty) {
      request.fields['expiry_date'] = expiryDate.trim();
    }
    if (file.bytes != null) {
      request.files.add(
        http.MultipartFile.fromBytes('file', file.bytes!, filename: file.name),
      );
    } else if (file.path != null) {
      request.files.add(await http.MultipartFile.fromPath('file', file.path!));
    } else {
      throw Exception('Selected document file is unavailable.');
    }
    final streamed = await request.send().timeout(const Duration(seconds: 45));
    final response = await http.Response.fromStream(streamed);
    if (response.statusCode != 201) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> reviewEmployeeDocument(
    int employeeId, {
    required int documentId,
    required String action,
    required String reason,
  }) async {
    final response = await http
        .patch(
          Uri.parse(
            '${ApiService.baseUrl}/employees/hrms/employees/$employeeId/documents/',
          ),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({
            'document_id': documentId,
            'action': action,
            'reason': reason,
          }),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> createEmployee(
    Map<String, dynamic> payload,
  ) async {
    final response = await http
        .post(
          Uri.parse('${ApiService.baseUrl}/employees/manage/'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 30));
    if (response.statusCode != 201) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> updateProfile(
    int employeeId,
    Map<String, dynamic> payload,
  ) async {
    final response = await http
        .patch(
          Uri.parse(
            '${ApiService.baseUrl}/employees/hrms/employees/$employeeId/profile/',
          ),
          headers: await ApiService.authHeaders(),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> updateLifecycle(
    int employeeId,
    Map<String, dynamic> payload,
  ) async {
    final response = await http
        .patch(
          Uri.parse('${ApiService.baseUrl}/employees/hrms/employees/$employeeId/'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> lifecycleAction(
    int employeeId,
    String action, {
    String note = '',
    Map<String, dynamic> extra = const {},
  }) async {
    final response = await http
        .post(
          Uri.parse(
            '${ApiService.baseUrl}/employees/hrms/employees/$employeeId/action/',
          ),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({'action': action, 'note': note, ...extra}),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> _getMap(String path) async {
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}$path'),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  String _message(http.Response response) {
    try {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return (data['message'] ??
              data['detail'] ??
              'Corporate HRMS request failed.')
          .toString();
    } catch (_) {
      return 'Corporate HRMS request failed (HTTP ${response.statusCode}).';
    }
  }
}
