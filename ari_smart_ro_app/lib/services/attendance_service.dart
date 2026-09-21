import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/attendance_model.dart';
import 'api_service.dart';
import 'device_identity_service.dart';

class AttendanceService {
  Future<Map<String, String>> _headers() async {
    final token = await ApiService.getAccessToken();

    return {
      "Authorization": "Bearer $token",
      "Content-Type": "application/json",
    };
  }

  // ===========================
  // CHECK IN
  // ===========================

  Future<AttendanceActionResult> checkIn({
    required double latitude,
    required double longitude,
    required String selfiePath,
  }) async {
    final token = await ApiService.getAccessToken();
    final deviceId = await DeviceIdentityService.getOrCreate();

    final request = http.MultipartRequest(
      "POST",
      Uri.parse("${ApiService.baseUrl}/attendance/check-in/"),
    );

    request.headers["Authorization"] = "Bearer $token";

    request.fields["latitude"] = latitude.toString();
    request.fields["longitude"] = longitude.toString();
    request.fields["device_id"] = deviceId;

    request.files.add(await http.MultipartFile.fromPath("selfie", selfiePath));

    try {
      final response = await request.send();
      final body = await response.stream.bytesToString();
      final success = response.statusCode == 200 || response.statusCode == 201;
      String message = success
          ? 'Checked in successfully.'
          : 'Check-in failed.';
      double? distanceMeters;

      try {
        final decoded = jsonDecode(body);
        if (decoded is Map<String, dynamic>) {
          final serverMessage = decoded['message'] ?? decoded['detail'];
          if (serverMessage != null &&
              serverMessage.toString().trim().isNotEmpty) {
            message = serverMessage.toString().trim();
          }
          final distance = decoded['distance_from_office_meters'];
          if (distance is num) distanceMeters = distance.toDouble();
        }
      } catch (_) {
        // Keep the safe fallback when the server returns a non-JSON response.
      }

      return AttendanceActionResult(
        success: success,
        message: message,
        statusCode: response.statusCode,
        distanceFromOfficeMeters: distanceMeters,
      );
    } catch (_) {
      return const AttendanceActionResult(
        success: false,
        message:
            'Unable to connect to the server. Check the network and try again.',
        statusCode: 0,
      );
    }
  }

  // ===========================
  // CHECK OUT
  // ===========================

  Future<AttendanceActionResult> checkOut() async {
    final response = await http.post(
      Uri.parse("${ApiService.baseUrl}/attendance/check-out/"),
      headers: await _headers(),
    );

    final success = response.statusCode == 200 || response.statusCode == 201;
    var message = success ? 'Checked out successfully.' : 'Check-out failed.';
    try {
      final data = jsonDecode(response.body);
      if (data is Map) {
        message = (data['message'] ?? data['detail'] ?? message).toString();
      }
    } catch (_) {}
    return AttendanceActionResult(
      success: success,
      message: message,
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> overtimeStatus() async {
    final response = await http.get(
      Uri.parse("${ApiService.baseUrl}/attendance/overtime/"),
      headers: await _headers(),
    );
    if (response.statusCode != 200) {
      throw Exception(_message(response, 'Unable to load overtime status.'));
    }
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<String> requestOvertime({
    required double hours,
    required String reason,
  }) async {
    final response = await http.post(
      Uri.parse("${ApiService.baseUrl}/attendance/overtime/"),
      headers: await _headers(),
      body: jsonEncode({'hours': hours, 'reason': reason}),
    );
    if (response.statusCode != 201) {
      throw Exception(_message(response, 'Unable to request overtime.'));
    }
    final data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    return (data['message'] ?? 'Overtime request sent.').toString();
  }

  Future<String> startOvertime() async {
    final response = await http.post(
      Uri.parse("${ApiService.baseUrl}/attendance/overtime/start/"),
      headers: await _headers(),
    );
    if (response.statusCode != 200) {
      throw Exception(_message(response, 'Unable to start overtime.'));
    }
    final data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    return (data['message'] ?? 'Approved overtime started.').toString();
  }

  Future<String> stopOvertime() async {
    final response = await http.post(
      Uri.parse("${ApiService.baseUrl}/attendance/overtime/stop/"),
      headers: await _headers(),
    );
    if (response.statusCode != 200) {
      throw Exception(_message(response, 'Unable to stop overtime.'));
    }
    final data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    return (data['message'] ?? 'Overtime stopped.').toString();
  }

  String _message(http.Response response, String fallback) {
    try {
      final data = jsonDecode(response.body);
      if (data is Map) {
        return (data['detail'] ?? data['message'] ?? fallback).toString();
      }
    } catch (_) {}
    return fallback;
  }

  // ===========================
  // TODAY ATTENDANCE
  // ===========================

  Future<AttendanceModel?> todayAttendance() async {
    final response = await http.get(
      Uri.parse("${ApiService.baseUrl}/attendance/today/"),
      headers: await _headers(),
    );
    print(response.statusCode);
    print(response.body);
    print("TODAY STATUS : ${response.statusCode}");
    print(response.body);

    if (response.statusCode == 200) {
      return AttendanceModel.fromJson(jsonDecode(response.body));
    }

    return null;
  }

  // ===========================
  // HISTORY
  // ===========================

  Future<List<AttendanceModel>> history() async {
    final response = await http.get(
      Uri.parse("${ApiService.baseUrl}/attendance/history/"),
      headers: await _headers(),
    );

    print("HISTORY STATUS : ${response.statusCode}");
    print(response.body);

    if (response.statusCode == 200) {
      final List data = jsonDecode(response.body);
      return data.map((e) => AttendanceModel.fromJson(e)).toList();
    }

    return [];
  }
}

class AttendanceActionResult {
  final bool success;
  final String message;
  final int statusCode;
  final double? distanceFromOfficeMeters;

  const AttendanceActionResult({
    required this.success,
    required this.message,
    required this.statusCode,
    this.distanceFromOfficeMeters,
  });
}
