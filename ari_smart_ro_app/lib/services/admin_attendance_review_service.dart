import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class AdminAttendanceReviewService {
  Future<List<Map<String, dynamic>>> getReviews({String status = 'PENDING'}) async {
    final response = await http.get(
      Uri.parse('${ApiService.baseUrl}/attendance/admin/reviews/?status=$status'),
      headers: await ApiService.authHeaders(),
    );

    if (response.statusCode != 200) {
      throw Exception('Unable to load attendance reviews');
    }

    final data = jsonDecode(response.body) as List;
    return data.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<String> updateReview({
    required int attendanceId,
    required String action,
    String note = '',
  }) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/attendance/admin/reviews/$attendanceId/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({
        'action': action,
        'note': note,
      }),
    );

    Map<String, dynamic> data = <String, dynamic>{};
    if (response.body.isNotEmpty) {
      data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    }

    if (response.statusCode != 200) {
      throw Exception(data['message']?.toString() ?? 'Unable to update review');
    }

    return data['message']?.toString() ?? 'Review updated';
  }
}
