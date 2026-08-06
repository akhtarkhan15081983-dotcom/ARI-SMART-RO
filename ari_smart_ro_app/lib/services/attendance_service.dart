import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import '../models/attendance_model.dart';
import 'api_service.dart';

class AttendanceService {
  final storage = const FlutterSecureStorage();

  Future<Map<String, String>> _headers() async {
    final token = await storage.read(key: "access");

    return {
      "Authorization": "Bearer $token",
      "Content-Type": "application/json",
    };
  }

  // ===========================
  // CHECK IN
  // ===========================

  Future<bool> checkIn({
    required double latitude,
    required double longitude,
    required String selfiePath,
  }) async {
    final token = await storage.read(key: "access");

    var request = http.MultipartRequest(
      "POST",
      Uri.parse(
        "${ApiService.baseUrl}/attendance/check-in/",
      ),
    );

    request.headers["Authorization"] = "Bearer $token";

    request.fields["latitude"] = latitude.toString();
    request.fields["longitude"] = longitude.toString();

    request.files.add(
      await http.MultipartFile.fromPath(
        "selfie",
        selfiePath,
      ),
    );

    final response = await request.send();

    final body = await response.stream.bytesToString();

    print("CHECK IN STATUS : ${response.statusCode}");
    print(body);

    return response.statusCode == 200 ||
        response.statusCode == 201;
  }

  // ===========================
  // CHECK OUT
  // ===========================

  Future<bool> checkOut() async {
    final response = await http.post(
      Uri.parse(
        "${ApiService.baseUrl}/attendance/check-out/",
      ),
      headers: await _headers(),
    );

    print("CHECK OUT STATUS : ${response.statusCode}");
    print(response.body);

    return response.statusCode == 200 ||
        response.statusCode == 201;
  }

  // ===========================
  // TODAY ATTENDANCE
  // ===========================

  Future<AttendanceModel?> todayAttendance() async {
    final response = await http.get(
      Uri.parse(
        "${ApiService.baseUrl}/attendance/today/",
      ),
      headers: await _headers(),
    );

    print("TODAY STATUS : ${response.statusCode}");
    print(response.body);

    if (response.statusCode == 200) {
      return AttendanceModel.fromJson(
        jsonDecode(response.body),
      );
    }

    return null;
  }

  // ===========================
  // HISTORY
  // ===========================

  Future<List<AttendanceModel>> history() async {
    final response = await http.get(
      Uri.parse(
        "${ApiService.baseUrl}/attendance/history/",
      ),
      headers: await _headers(),
    );

    print("HISTORY STATUS : ${response.statusCode}");
    print(response.body);

    if (response.statusCode == 200) {
      final List data = jsonDecode(response.body);

      return data
          .map(
            (e) => AttendanceModel.fromJson(e),
          )
          .toList();
    }

    return [];
  }
}