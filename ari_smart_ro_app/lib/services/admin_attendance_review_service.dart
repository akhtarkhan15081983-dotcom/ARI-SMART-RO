import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class AdminAttendanceReviewService {
  Future<List<Map<String, dynamic>>> getReviews({
    String status = 'PENDING',
  }) async {
    return _fetchAll(
      '/attendance/admin/reviews/',
      query: {'status': status},
      errorMessage: 'Unable to load attendance reviews',
    );
  }

  Future<List<Map<String, dynamic>>> getOvertimeRequests({
    String status = '',
  }) async {
    return _fetchAll(
      '/attendance/admin/overtime/',
      query: status.isEmpty ? const {} : {'status': status},
      errorMessage: 'Unable to load overtime requests',
    );
  }

  Future<List<Map<String, dynamic>>> _fetchAll(
    String path, {
    required Map<String, String> query,
    required String errorMessage,
  }) async {
    const pageSize = 200;
    var page = 1;
    final rows = <Map<String, dynamic>>[];

    while (true) {
      final uri = Uri.parse('${ApiService.baseUrl}$path').replace(
        queryParameters: {
          ...query,
          'page': '$page',
          'page_size': '$pageSize',
        },
      );
      final response = await http.get(
        uri,
        headers: await ApiService.authHeaders(),
      );
      if (response.statusCode != 200) {
        throw Exception(errorMessage);
      }
      final decoded = jsonDecode(response.body);
      if (decoded is List) {
        rows.addAll(
          decoded.map((e) => Map<String, dynamic>.from(e as Map)),
        );
        break;
      }
      final body = Map<String, dynamic>.from(decoded as Map);
      final pageRows = (body['results'] as List<dynamic>? ?? const [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList(growable: false);
      rows.addAll(pageRows);
      if (body['has_more'] != true || pageRows.isEmpty) break;
      page = (body['next_page'] as num?)?.toInt() ?? (page + 1);
    }
    return rows;
  }

  Future<String> reviewOvertime({
    required int requestId,
    required String action,
    double? approvedHours,
    String note = '',
  }) async {
    final response = await http.post(
      Uri.parse(
        '${ApiService.baseUrl}/attendance/admin/overtime/$requestId/',
      ),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({
        'action': action,
        if (approvedHours != null) 'approved_hours': approvedHours,
        'note': note,
      }),
    );
    Map<String, dynamic> data = <String, dynamic>{};
    if (response.body.isNotEmpty) {
      data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    }
    if (response.statusCode != 200) {
      throw Exception(
        (data['detail'] ?? data['message'] ?? 'Unable to review overtime')
            .toString(),
      );
    }
    return (data['message'] ?? 'Overtime updated').toString();
  }

  Future<String> updateReview({
    required int attendanceId,
    required String action,
    String note = '',
  }) async {
    final response = await http.post(
      Uri.parse(
        '${ApiService.baseUrl}/attendance/admin/reviews/$attendanceId/',
      ),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({'action': action, 'note': note}),
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
