import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class CallingDeskService {
  Future<Map<String, dynamic>> list({String query = '', String outcome = 'ALL'}) async {
    final uri = Uri.parse('${ApiService.baseUrl}/customers/calling-desk/').replace(
      queryParameters: {
        if (query.trim().isNotEmpty) 'q': query.trim(),
        if (outcome != 'ALL') 'outcome': outcome,
      },
    );
    final response = await http.get(uri, headers: await ApiService.authHeaders());
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> update(
    int id, {
    required String outcome,
    required String note,
    DateTime? nextFollowUp,
    int durationSeconds = 0,
  }) async {
    final response = await http.patch(
      Uri.parse('${ApiService.baseUrl}/customers/calling-desk/$id/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({
        'outcome': outcome,
        'note': note.trim(),
        'next_follow_up_at': nextFollowUp?.toUtc().toIso8601String() ?? '',
        'duration_seconds': durationSeconds,
      }),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> createLead({
    int? customerId,
    String customerName = '',
    String phone = '',
    String city = '',
    String requestType = 'SERVICE',
    String priority = 'NORMAL',
    String planName = '',
    String notes = '',
  }) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/customers/calling-desk/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({
        if (customerId != null) 'customer_id': customerId,
        'customer_name': customerName.trim(),
        'phone': phone.trim(),
        'city': city.trim(),
        'request_type': requestType,
        'priority': priority,
        'plan_name': planName.trim(),
        'notes': notes.trim(),
      }),
    );
    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception(_message(response));
    }
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  String _message(http.Response response) {
    try {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return (data['detail'] ?? data['message'] ?? 'Calling desk request failed.').toString();
    } catch (_) {
      return 'Calling desk request failed (HTTP ${response.statusCode}).';
    }
  }
}
